import numpy as np
import json
from skimage import measure

def to_python(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [to_python(item) for item in obj]
    if isinstance(obj, (list, tuple)):
        return [to_python(item) for item in obj]
    if isinstance(obj, dict):
        return {k: to_python(v) for k, v in obj.items()}
    return obj

class Simple3DEngine:
    def __init__(self):
        self.colors = {
            1: '#ff3d3d',
            2: '#3dff8a',
            3: '#4d9dff',
            4: '#ffb84d',
        }

    def generate_html(self, mask_volume: np.ndarray, spacing):
        if mask_volume is None or np.sum(mask_volume) == 0:
            return "<div style='color:white;padding:40px'>暂无有效分割结果</div>"

        mask = mask_volume.astype(np.uint8)
        spacing = to_python(spacing)
        labels = [int(l) for l in np.unique(mask) if l > 0]
        meshes = []

        for lab in labels:
            binary = (mask == lab).astype(np.float32)
            try:
                # 更精细的采样，更平滑
                verts, faces, _, _ = measure.marching_cubes(
                    binary,
                    level=0.5,
                    spacing=spacing,
                    step_size=1,  # 更精细
                    allow_degenerate=False
                )
            except:
                continue

            if len(verts) == 0:
                continue

            verts = to_python(verts)
            faces = to_python(faces)

            meshes.append({
                "vertices": verts,
                "triangles": faces,
                "color": self.colors.get(lab, "#ffffff")
            })

        if not meshes:
            return "<div style='color:white;padding:40px'>未提取到3D模型</div>"

        mesh_json = json.dumps(meshes)

        html = """
<!DOCTYPE html>
<html style="margin:0;padding:0;">
<head>
<meta charset="utf-8">
<style>
body{margin:0;background:#0a0a0a;height:680px;overflow:hidden;}
canvas{width:100%;height:100%;display:block;}
</style>
<script src="https://cdn.bootcdn.net/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
<div id="container"></div>
<script>
const meshes = """ + mesh_json + """

window.onload = function() {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);

    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / 680, 0.1, 3000);
    camera.position.set(280, 280, 450);

    const renderer = new THREE.WebGLRenderer({ antialias:true, alpha:true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, 680);
    document.getElementById('container').appendChild(renderer.domElement);

    // 柔和多光源，质感瞬间高级
    const light1 = new THREE.DirectionalLight(0xffffff, 0.85);
    light1.position.set(100, 200, 300);
    scene.add(light1);

    const light2 = new THREE.DirectionalLight(0xffffff, 0.45);
    light2.position.set(-300, -100, 200);
    scene.add(light2);

    const ambient = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambient);

    const group = new THREE.Group();
    meshes.forEach(m => {
        const geo = new THREE.BufferGeometry();
        const vertices = m.vertices.flat();
        const triangles = m.triangles.flat();

        geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
        geo.setIndex(triangles);
        geo.computeVertexNormals();

        // 光滑材质 + 半透明 + 高级质感
        const mat = new THREE.MeshPhongMaterial({
            color: m.color,
            transparent: true,
            opacity: 0.9,
            shininess: 80,
            side: THREE.DoubleSide
        });

        const mesh = new THREE.Mesh(geo, mat);
        group.add(mesh);
    });

    scene.add(group);

    // 自动旋转 + 鼠标控制
    let autoRotate = true;
    let dragging = false, lastX=0, lastY=0;

    document.addEventListener('mousedown', e=>{ dragging=true; lastX=e.clientX; lastY=e.clientY; autoRotate=false; });
    document.addEventListener('mouseup', ()=>dragging=false);
    document.addEventListener('mousemove', e=>{
        if(!dragging) return;
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        group.rotation.y += dx * 0.004;
        group.rotation.x += dy * 0.004;
        lastX=e.clientX; lastY=e.clientY;
    });

    document.addEventListener('wheel', e=>{ camera.position.z += e.deltaY * 0.4; });

    function animate(){
        requestAnimationFrame(animate);
        if(autoRotate) group.rotation.y += 0.004;
        renderer.render(scene,camera);
    }
    animate();
};
</script>
</body>
</html>
        """
        return html