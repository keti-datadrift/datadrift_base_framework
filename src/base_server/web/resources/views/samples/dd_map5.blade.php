<!DOCTYPE html>
<meta charset="utf-8">
<style>
.boundary {
  fill: none;
  stroke: black;
  stroke-dasharray: 2, 2;
  stroke-linejoin: round;
}
.place-label {
  font-size: 9px;
  fill: yellow;
}
</style>
<body>
<!-- 라이브러리 로드 -->
<script src="js/d3.v3.min.js"></script>
<script src="js/topojson.v0.min.js"></script>
<script>
// SVG 영역 생성 ------ (*1)
var width = 1024, height = 1024;
var svg = d3.select("body")
  .append("svg")
  .attr({"width":width, "height":height});

// 파일 읽기 ---- (*2)
d3.json("data/korea-topo.json", function(err, map) {
  // 그리기 위한 오브젝트 획득  ------ (*3)
  var geo = map.objects["korea-geo"];
  var map_o = topojson.object(map, geo);
  
  // 축척 지정 ----- (*4)
  var projection = d3.geo.mercator()
        .center([137, 35])
        .scale(2000)
        .translate([width / 2, height / 2]);
  
  // 패스 작성 ---- (*5)
  var path = d3.geo.path()
    .projection(projection);

  // SVG에 추가 ---- (*6)
  svg.append("path")
     .datum(map_o)
     .attr("d", path);

  // 색 설정 ---- (*7)
  svg.selectAll("path").attr("fill", "green");

  // 경계선 ---- (*8)
  var mesh = topojson.mesh(
    map, geo, 
    function(a, b) {
      return a !== b; 
    });
  svg.append("path")
     .datum(mesh)
     .attr("d", path)
     .attr("class", "boundary");
  
  // 도 이름 표시 ---- (*9)
  svg.selectAll(".place-label")
     .data(map_o.geometries)
     .enter()
       .append("text")
       .attr("class", function(d) {
          return "place-label";
       })
       .attr("transform", function(d) {
          return "translate(" + path.centroid(d) + ")";
       })
       .text(function(d) {
          var s = d.properties.name_local;
          if (!s) return;
          if (s == "서울특별시") return s;
          else return; // ---- (*10)
          return s;
       });
});
</script>
</body>
</html>

