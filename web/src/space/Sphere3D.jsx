import { useEffect, useRef } from 'react'
import * as THREE from 'three'

/**
 * Corpo celeste in 3D: una sfera con la mappa globale (proiezione
 * equirettangolare) che ruota lentamente. Si trascina per girarla e si usa
 * la rotella (o due dita) per avvicinarsi.
 */
export default function Sphere3D({ texture, flattening = 0, onLoad }) {
  const mountRef = useRef(null)
  const state = useRef({})

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
    let spin = 0.0015
    const canvas = renderer.domElement
    canvas.style.touchAction = 'none'
    const pointers = new Map()
    canvas.addEventListener('pointerdown', (e) => {
      pointers.set(e.pointerId, e)
      drag = { x: e.clientX, y: e.clientY }
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
    const release = (e) => { pointers.delete(e.pointerId); if (pointers.size === 0) { drag = null; spin = 0.0015 } }
    canvas.addEventListener('pointerup', release)
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

    state.current = { mesh, material, renderer, camera }
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
    new THREE.TextureLoader().load(texture, (map) => {
      if (cancelled) { map.dispose(); return }
      map.colorSpace = THREE.SRGBColorSpace
      map.anisotropy = 8
      material.map?.dispose()
      material.map = map
      material.needsUpdate = true
      onLoad?.()
    })
    mesh.scale.set(1, 1 - flattening, 1)
    camera.position.z = 4.2
    return () => { cancelled = true }
  }, [texture, flattening, onLoad])

  return <div ref={mountRef} className="sphere3d" />
}
