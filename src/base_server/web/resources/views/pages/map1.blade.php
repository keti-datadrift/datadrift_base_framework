<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="utf-8">
  <title>Flight Paths using Edge Bundling</title>

  <script src="https://d3js.org/d3.v5.min.js"></script>
  <script src="https://unpkg.com/topojson@3"></script>
  <script src="https://unpkg.com/d3-delaunay@4"></script>
  <script src="https://unpkg.com/d3-geo-voronoi@1"></script>

  <link href="css/style4flightmap.css" rel="stylesheet">
</head>

<body>

<!-- must be 960x600 to match topojson us atlas files -->
<svg width="960" height="600">
  <!-- must be in this order for drawing -->
  <g id="basemap"></g>
  <g id="flights"></g>
  <g id="airports"></g>
  <g id="voronoi"></g>
  <text id="tooltip" style="display: none;"></text>
</svg>

<script src="js/script4flightmap.js"></script>

</body>
</html>