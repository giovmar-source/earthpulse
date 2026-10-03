import { useEffect, useRef } from 'react'
import * as THREE from 'three'

const SNAP_PX = 18           // distanza (pixel) entro cui il cursore "aggancia" un sito
const SITE_COLOR = 0xffffff
const SITE_HOVER = 0xf2b33d

/** Punto della superficie (lat, lon in gradi) nelle coordinate della SphereGeometry di three.js. */
function surfacePoint(lat, lon, radius) {
  const phi = ((lon + 180) / 360) * Math.PI * 2
  const theta = ((90 - lat) / 180) * Math.PI
  return new THREE.Vector3(-Math.cos(phi) * Math.sin(theta), Math.cos(theta), Math.sin(phi) * Math.sin(theta)).multiplyScalar(radius)
}

/**
 * Anelli (es. Saturno) sul piano dell'equatore: raggi in raggi del pianeta e
 * fasce con opacità indicativa, disegnate come trama radiale.
 */
function makeRings({ inner, outer, bands }) {
  const geometry = new THREE.RingGeometry(inner, outer, 256, 1)
  // Coordinate della trama: u = distanza dal centro (0 = bordo interno, 1 = esterno)
  const pos = geometry.attributes.position
  const uv = geometry.attributes.uv
  const v = new THREE.Vector3()
  for (let i = 0; i < pos.count; i += 1) {
    v.fromBufferAttribute(pos, i)
    uv.setXY(i, (v.length() - inner) / (outer - inner), 0.5)
  }
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 1
  const ctx = canvas.getContext('2d')
  for (const [from, to, color, alpha] of bands) {
    const x0 = ((from - inner) / (outer - inner)) * canvas.width
    const x1 = ((to - inner) / (outer - inner)) * canvas.width
    ctx.fillStyle = color
    ctx.globalAlpha = alpha
    ctx.fillRect(x0, 0, Math.max(1, x1 - x0), 1)
  }
  const map = new THREE.CanvasTexture(canvas)
  map.colorSpace = THREE.SRGBColorSpace
  const material = new THREE.MeshStandardMaterial({
    map, transparent: true, side: THREE.DoubleSide, roughness: 1, metalness: 0, depthWrite: false,
  })
  const mesh = new THREE.Mesh(geometry, material)
  mesh.rotation.x = -Math.PI / 2           // dal piano XY al piano dell'equatore (XZ)
  return mesh
}

/**
 * Corpo celeste in 3D: una sfera con la mappa globale (proiezione
 * equirettangolare) che ruota lentamente. Si trascina per girarla e si usa
 * la rotella (o due dita) per avvicinarsi. I siti di atterraggio si
 * "agganciano" quando il cursore passa vicino: compare il nome e la manina.
 */
export default function Sphere3D({ texture, flattening = 0, onTextureState, onPick, onPickSite, marker, sites,
  rings = null, distance = 4.2 }) {
  const mountRef = useRef(null)
  const tipRef = useRef(null)
  const state = useRef({})
  // Callback sempre aggiornate senza ricreare la scena o ricaricare la mappa
  const callbacks = useRef({})
  callbacks.current = { onTextureState, onPick, onPickSite }

  // Scena, camera e animazione: una sola volta
  useEffect(() => {
    const mount = mountRef.current
    const tip = tipRef.current
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    mount.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100)
    camera.position.set(0, 0, 4.2)
    scene.add(new THREE.AmbientLight(0xffffff, 0.55))
    const sun = new THREE.DirectionalLight(0xffffff, 2.2)
    sun.position.set(-4, 1.5, 3)
    scene.add(sun)

    const material = new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0 })
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 128, 64), material)
    mesh.rotation.x = 0.12
    scene.add(mesh)

    // Segnaposto del punto scelto (figlio della sfera: gira con lei)
    const pin = new THREE.Mesh(new THREE.SphereGeometry(0.018, 16, 12), new THREE.MeshBasicMaterial({ color: 0xf2b33d }))
    pin.visible = false
    mesh.add(pin)
    // Siti di atterraggio: punti bianchi sulla superficie
    const siteGroup = new THREE.Group()
    mesh.add(siteGroup)
    const raycaster = new THREE.Raycaster()

    // Stelle di sfondo
    const starGeometry = new THREE.BufferGeometry()
    const positions = new Float32Array(1500 * 3)
    for (let i = 0; i < positions.length; i += 3) {
      const v = new THREE.Vector3().randomDirection().multiplyScalar(30 + Math.random() * 20)
      positions.set([v.x, v.y, v.z], i)
    }
    starGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    scene.add(new THREE.Points(starGeometry, new THREE.PointsMaterial({ color: 0xffffff, size: 0.08, sizeAttenuation: true })))

    function resize() {
      const { clientWidth: w, clientHeight: h } = mount
      renderer.setSize(w, h, false)
      camera.aspect = w / Math.max(h, 1)
      camera.updateProjectionMatrix()
    }
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(mount)

    const zoom = (factor) => {
      const base = state.current.distance || 4.2
      camera.position.z = THREE.MathUtils.clamp(camera.position.z * factor, 1.6, base * 2)
    }

    // Sito di atterraggio più vicino al cursore, solo se sulla faccia visibile
    const world = new THREE.Vector3()
    const toCamera = new THREE.Vector3()
    function nearestSite(clientX, clientY) {
      const rect = renderer.domElement.getBoundingClientRect()
      let best = null
      for (const dot of siteGroup.children) {
        dot.getWorldPosition(world)
        toCamera.copy(camera.position).sub(world)
        if (world.dot(toCamera) <= 0) continue                 // dall'altra parte del corpo
        const p = world.clone().project(camera)
        const x = rect.left + ((p.x + 1) / 2) * rect.width
        const y = rect.top + ((1 - p.y) / 2) * rect.height
        const d = Math.hypot(x - clientX, y - clientY)
        if (d <= SNAP_PX && (!best || d < best.d)) best = { dot, d, x: x - rect.left, y: y - rect.top }
      }
      return best
    }
    let hovered = null
    let idleSpin = 0.0015            // rotazione lenta quando nessuno tocca la sfera
    let spin = idleSpin
    let drag = null
    function setHover(found) {
      if (hovered && hovered !== found?.dot) {
        hovered.material.color.setHex(SITE_COLOR)
        hovered.scale.setScalar(1)
      }
      hovered = found?.dot || null
      renderer.domElement.style.cursor = hovered ? 'pointer' : 'grab'
      // Sopra un sito il globo si ferma, così il punto resta sotto il cursore
      if (!drag) spin = hovered ? 0 : idleSpin
      if (hovered) {
        hovered.material.color.setHex(SITE_HOVER)
        hovered.scale.setScalar(1.8)
        const site = hovered.userData.site
        tip.textContent = `${site.name} · ${site.date.slice(0, 4)}`
        tip.style.left = `${found.x}px`
        tip.style.top = `${found.y}px`
        tip.hidden = false
      } else {
        tip.hidden = true
      }
    }

    // Trascinamento e zoom
    const canvas = renderer.domElement
    canvas.style.touchAction = 'none'
    canvas.style.cursor = 'grab'
    const pointers = new Map()
    let pressed = null
    canvas.addEventListener('pointerdown', (e) => {
      pointers.set(e.pointerId, e)
      drag = { x: e.clientX, y: e.clientY }
      pressed = { x: e.clientX, y: e.clientY }
      spin = 0
      canvas.setPointerCapture(e.pointerId)
    })
    canvas.addEventListener('pointermove', (e) => {
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()]
        const before = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)
        pointers.set(e.pointerId, e)
        const [c, d] = [...pointers.values()]
        const after = Math.hypot(c.clientX - d.clientX, c.clientY - d.clientY)
        zoom(before / after)
        return
      }
      if (!drag) {                    // nessun tasto premuto: aggancio dei siti
        setHover(siteGroup.children.length ? nearestSite(e.clientX, e.clientY) : null)
        return
      }
      pointers.set(e.pointerId, e)
      setHover(null)
      mesh.rotation.y += (e.clientX - drag.x) * 0.005
      mesh.rotation.x = THREE.MathUtils.clamp(mesh.rotation.x + (e.clientY - drag.y) * 0.005, -1.2, 1.2)
      drag = { x: e.clientX, y: e.clientY }
    })
    canvas.addEventListener('pointerleave', () => setHover(null))
    const release = (e) => { pointers.delete(e.pointerId); if (pointers.size === 0) { drag = null; spin = hovered ? 0 : idleSpin } }
    // Un tocco senza trascinare: sito di atterraggio vicino, altrimenti punto della superficie
    canvas.addEventListener('pointerup', (e) => {
      const tap = pressed && Math.hypot(e.clientX - pressed.x, e.clientY - pressed.y) < 5
      pressed = null
      release(e)
      if (!tap) return
      const site = siteGroup.children.length ? nearestSite(e.clientX, e.clientY) : null
      if (site && callbacks.current.onPickSite) {
        callbacks.current.onPickSite(site.dot.userData.site)
        return
      }
      if (!callbacks.current.onPick) return
      const rect = canvas.getBoundingClientRect()
      const ndc = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1)
      raycaster.setFromCamera(ndc, camera)
      const hit = raycaster.intersectObject(mesh, false)[0]
      if (!hit?.uv) return
      callbacks.current.onPick({ lat: hit.uv.y * 180 - 90, lon: hit.uv.x * 360 - 180 })
    })
    canvas.addEventListener('pointercancel', release)
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault()
      zoom(1 + e.deltaY * 0.001)
    }, { passive: false })

    let frame
    function animate() {
      mesh.rotation.y += spin
      renderer.render(scene, camera)
      frame = requestAnimationFrame(animate)
    }
    animate()

    state.current = { mesh, material, renderer, camera, pin, siteGroup, setSpin: (v) => { idleSpin = v; spin = v } }
    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      material.map?.dispose()
      material.dispose()
      mesh.geometry.dispose()
      renderer.dispose()
      mount.removeChild(canvas)
    }
  }, [])

  // Cambio di corpo: nuova mappa (e schiacciamento ai poli per i giganti)
  useEffect(() => {
    const { material, mesh } = state.current
    if (!material) return
    let cancelled = false
    callbacks.current.onTextureState?.('loading')
    new THREE.TextureLoader().load(texture, (map) => {
      if (cancelled) { map.dispose(); return }
      map.colorSpace = THREE.SRGBColorSpace
      map.anisotropy = 8
      material.map?.dispose()
      material.map = map
      material.needsUpdate = true
      callbacks.current.onTextureState?.('ok')
    }, undefined, () => {
      if (!cancelled) callbacks.current.onTextureState?.('error')
    })
    mesh.scale.set(1, 1 - flattening, 1)
    return () => { cancelled = true }
  }, [texture, flattening])

  // Anelli (Saturno)
  useEffect(() => {
    const { mesh } = state.current
    if (!mesh || !rings) return undefined
    const ringMesh = makeRings(rings)
    mesh.add(ringMesh)
    return () => {
      mesh.remove(ringMesh)
      ringMesh.geometry.dispose()
      ringMesh.material.map.dispose()
      ringMesh.material.dispose()
    }
  }, [rings])

  // Cambio di corpo: inquadratura iniziale (più lontana se ci sono gli anelli)
  useEffect(() => {
    state.current.distance = distance
    if (state.current.camera) state.current.camera.position.z = distance
  }, [distance, texture])

  // Siti di atterraggio
  useEffect(() => {
    const { siteGroup } = state.current
    if (!siteGroup) return
    siteGroup.children.forEach((child) => { child.geometry.dispose(); child.material.dispose() })
    siteGroup.clear()
    for (const site of sites || []) {
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.011, 12, 10), new THREE.MeshBasicMaterial({ color: SITE_COLOR }))
      dot.position.copy(surfacePoint(site.lat, site.lon, 1.003))
      dot.userData.site = site
      siteGroup.add(dot)
    }
  }, [sites])

  // Segnaposto: stessa corrispondenza tra coordinate e mappa della SphereGeometry di three.js
  useEffect(() => {
    const { pin, setSpin } = state.current
    if (!pin) return
    if (!marker) { pin.visible = false; setSpin?.(0.0015); return }
    pin.position.copy(surfacePoint(marker.lat, marker.lon, 1.004))
    pin.visible = true
    setSpin?.(0)
  }, [marker])

  return (
    <div ref={mountRef} className="sphere3d">
      <div ref={tipRef} className="site-tip" hidden />
    </div>
  )
}
