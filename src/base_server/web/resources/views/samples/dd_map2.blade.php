<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <style>
    svg { background-color: #eee; }
    svg .municipality { fill: red; }
    svg .municipality:hover { stroke: #333; }
    svg .municipality.p0 { fill: rgb(247,251,255); }
    svg .municipality.p1 { fill: rgb(222,235,247); }
    svg .municipality.p2 { fill: rgb(198,219,239); }
    svg .municipality.p3 { fill: rgb(158,202,225); }
    svg .municipality.p4 { fill: rgb(107,174,214); }
    svg .municipality.p5 { fill: rgb(66,146,198); }
    svg .municipality.p6 { fill: rgb(33,113,181); }
    svg .municipality.p7 { fill: rgb(8,81,156); }
    svg .municipality.p8 { fill: rgb(8,48,107); }
    svg text { font-size: 10px; }
    </style>
  </head>
  <body>
    <div id="chart"></div>
    <script src="http://d3js.org/d3.v3.min.js"></script>
    <script src="http://d3js.org/topojson.v1.min.js"></script>
    <script src="http://d3js.org/queue.v1.min.js"></script>
    <script>
    var width = 960,
        height = 500;

    var svg = d3.select("#chart").append("svg")
        .attr("width", width)
        .attr("height", height);

    var projection = d3.geo.mercator()
        .center([128, 36])
        .scale(4000)
        .translate([width/2, height/2]);

    var path = d3.geo.path()
        .projection(projection);

    var quantize = d3.scale.quantize()
        .domain([0, 1000])
        .range(d3.range(9).map(function(i) { return "p" + i; }));

    var popByName = d3.map();

    queue()
        .defer(d3.json, "data/municipalities-topo-simple.json")
        .defer(d3.csv, "data/population-edited.csv", function(d) {
            popByName.set(d.name, +d.population);
        })
        .await(ready);

    function ready(error, data) {
      var features = topojson.feature(data, data.objects["municipalities-geo"]).features;

      features.forEach(function(d) {
        d.properties.population = popByName.get(d.properties.name);
        d.properties.density = d.properties.population / path.area(d);
        d.properties.quantized = quantize(d.properties.density);
      });

      svg.selectAll("path")
          .data(features)
        .enter().append("path")
          .attr("class", function(d) { return "municipality " + d.properties.quantized; })
          .attr("d", path)
          .attr("id", function(d) { return d.properties.name; })
        .append("title")
        .text(function(d) { return d.properties.name + ": " + d.properties.population/10000 + "만 명" });

      svg.selectAll("text")
          .data(features.filter(function(d) { return d.properties.name.endsWith("시"); }))
        .enter().append("text")
          .attr("transform", function(d) { return "translate(" + path.centroid(d) + ")"; })
          .attr("dy", ".35em")
          .attr("class", "region-label")
          .text(function(d) { return d.properties.name; });
    }
    </script>
  </body>
</html>