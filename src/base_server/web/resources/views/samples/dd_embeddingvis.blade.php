<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Embedding Visualization with Three.js and D3.js</title>
    <style>
        body { margin: 0; }
        canvas { display: block; }
    </style>
</head>
<body>

<h1 style="text-align: center;">3D Embedding Vector Visualization</h1>

<div id="scene-container"></div>

<!-- Three.js 라이브러리 -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<!-- D3.js 라이브러리 -->
<script src="https://d3js.org/d3.v7.min.js"></script>

<script>
    // 임베딩 벡터 데이터 (3차원으로 축소된 벡터)
    const embeddingData = [
        { x: 0.1, y: 0.5, z: 0.3, label: "A" },
        { x: 0.4, y: 0.9, z: 0.1, label: "B" },
        { x: 0.7, y: 0.4, z: 0.8, label: "C" },
        { x: 0.6, y: 0.6, z: 0.2, label: "D" },
        { x: 0.2, y: 0.3, z: 0.9, label: "E" }
    ];

    // Three.js 초기 설정
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer();
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.getElementById('scene-container').appendChild(renderer.domElement);

    // 축과 그리드 설정 (참조용)
    const axesHelper = new THREE.AxesHelper(5);
    scene.add(axesHelper);

    // 포인트(벡터) 설정
    const geometry = new THREE.SphereGeometry(0.05, 32, 32); // 크기 0.05의 구
    const material = new THREE.MeshBasicMaterial({ color: 0x0077ff });

    embeddingData.forEach(d => {
        const sphere = new THREE.Mesh(geometry, material);
        sphere.position.set(d.x * 10 - 5, d.y * 10 - 5, d.z * 10 - 5); // 좌표 설정 (10배 확장 후 중앙으로 이동)
        scene.add(sphere);
    });

    // 카메라 위치
    camera.position.z = 10;

    // 애니메이션 루프 (회전)
    const animate = function () {
        requestAnimationFrame(animate);
        scene.rotation.y += 0.01; // 장면을 회전
        renderer.render(scene, camera);
    };

    animate();
</script>

</body>
</html>