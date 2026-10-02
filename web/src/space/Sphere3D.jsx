import { useEffect, useRef } from 'react'
import * as THREE from 'three'

/**
 * Corpo celeste in 3D: una sfera con la mappa globale (proiezione
 * equirettangolare) che ruota lentamente. Si trascina per girarla e si usa
 * la rotella (o due dita) per avvicinarsi.
 */
export default function Sphere3D({ texture, flattening = 0, onTextureState, onPick, marker }) {
  const mountRef = useRef(null)
  const state = useRef({})
  // Callback sempre aggiornate senza ricreare la scena o ricaricare la mappa
  const callbacks = useRef({})
  callbacks.current = { onTextureState, onPick }

  // Scena, camera e animazione: una sola volta
  useEffect(() => {
    const mount = mountRef.current
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
    const pin = new THREE.Mesh(
      new THREE.SphereGeometry(0.018, 16, 12),
      new THREE.MeshBasicMaterial({ color: 0xf2b33d }),
    )
    pin.visible = false
    mesh.add(pin)
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

    // Trascinamento e zoom
    let drag = null
    let idleSpin = 0.0015            // rotazione lenta quando nessuno tocca la sfera
    let spin = idleSpin
    const canvas = renderer.domElement
    canvas.style.touchAction = 'none'
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
        camera.position.z = THREE.MathUtils.clamp(camera.position.z * (before / after), 1.6, 8)
        return
      }
      pointers.set(e.pointerId, e)
      if (!drag) return
      mesh.rotation.y += (e.clientX - drag.x) * 0.005
      mesh.rotation.x = THREE.MathUtils.clamp(mesh.rotation.x + (e.clientY - drag.y) * 0.005, -1.2, 1.2)
      drag = { x: e.clientX, y: e.clientY }
    })
    const release = (e) => { pointers.delete(e.pointerId); if (pointers.size === 0) { drag = null; spin = idleSpin } }
    // Un tocco senza trascinare: punto della superficie -> latitudine e longitudine
    canvas.addEventListener('pointerup', (e) => {
      const tap = pressed && Math.hypot(e.clientX - pressed.x, e.clientY - pressed.y) < 5
      pressed = null
      release(e)
      if (!tap || !callbacks.current.onPick) return
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
      camera.position.z = THREE.MathUtils.clamp(camera.position.z * (1 + e.deltaY * 0.001), 1.6, 8)
    }, { passive: false })

    let frame
    function animate() {
      mesh.rotation.y += spin
      renderer.render(scene, camera)
      frame = requestAnimationFrame(animate)
    }
    animate()

    state.current = { mesh, material, renderer, camera, pin, setSpin: (v) => { idleSpin = v; spin = v } }
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

  // Cambio di corpo: nuova mappa (e schiacciamento ai poli per Giove)
  useEffect(() => {
    const { material, mesh, camera } = state.current
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

  // Cambio di corpo: inquadratura iniziale
  useEffect(() => {
    if (state.current.camera) state.current.camera.position.z = 4.2
  }, [flattening])

  // Segnaposto: stessa corrispondenza tra coordinate e mappa della SphereGeometry di three.js
  useEffect(() => {
    const { pin, setSpin } = state.current
    if (!pin) return
    if (!marker) { pin.visible = false; setSpin?.(0.0015); return }
    const phi = ((marker.lon + 180) / 360) * Math.PI * 2
    const theta = ((90 - marker.lat) / 180) * Math.PI
    pin.position.set(-Math.cos(phi) * Math.sin(theta), Math.cos(theta), Math.sin(phi) * Math.sin(theta)).multiplyScalar(1.004)
    pin.visible = true
    setSpin?.(0)
  }, [marker])

  return <div ref={mountRef} className="sphere3d" />
}
