<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <style>
        svg {
            background-color: #a8daf7;
        }
        svg circle {
            opacity: .5;
            stroke: white;
        }
        svg circle:hover { stroke: #333; }
        svg text {
            color: #333;
            font-size: 10px;
            pointer-events: none;
            text-anchor: middle;
        }
        svg .province {
            fill: #efefef;
            stroke: #fff;
        }
        svg .region-label {
          fill: #777;
          font-size: 12px;
          font-weight: 300;
          text-anchor: middle;
        }
        svg .legend circle {
          fill: none;
          stroke: #eee;
        }

        svg .legend text {
          fill: #fff;
          font: 10px sans-serif;
          text-anchor: middle;
        }
        #title {
          position: absolute;
          top: 10px;
          left: 600px;
          width: 350px;
          font-family: sans-serif;
          text-align: right;
        }
        #title p {
          font-size: 10pt;
        }
    </style>
  </head>
  <body>
    <div id="title">
      <h2>우리나라 도시별 인구수 시각화</h2>
      <p>우리나라 인구수를 도시별로 표시한 버블그래프입니다. (수치는 실제값과 다를 수 있습니다.)</p>
      <p>
        <a href="https://gist.github.com/e9t/826b20ae75b331f56b4e">Code</a> by <a href="http://lucypark.kr">Lucy Park</a>
        <br>
        <a href="http://opensource.org/licenses/Apache-2.0">Licensed with Apache 2.0</a>
      </p>

    </div>
    <div id="chart"></div>
    <script src="http://d3js.org/d3.v3.min.js"></script>
    <script src="http://d3js.org/queue.v1.min.js"></script>
    <script src="http://d3js.org/topojson.v1.min.js"></script>
    <script>
    var width = 960,
        height = 500;

    var colorScale = d3.scale.linear()
        .range(['yellowgreen', 'yellow']) // or use hex values
        .domain([20, 50]);

    var svg = d3.select("#chart").append("svg")
        .attr("width", width)
        .attr("height", height);

    var map = svg.append("g").attr("id", "map"),
        points = svg.append("g").attr("id", "cities");

    var projection = d3.geo.mercator()
        .center([128, 36])
        .scale(4000)
        .translate([width/3, height/2]);

    var path = d3.geo.path().projection(projection);

    var quantize = d3.scale.quantize()
        .domain([0, 12234630]) // FIXME: automate
        .range(d3.range(9).map(function(i) { return " p" + i; }));

    var popById = d3.map();
  
    var radius = d3.scale.sqrt()
        .domain([0, 1e6])
        .range([0, 15]);

    var legend = svg.append("g")
        .attr("class", "legend")
        .attr("transform", "translate(" + (width/2 + 100) + "," + (height - 20) + ")")
      .selectAll("g")
        .data([1e6, 5e6, 1e7])
      .enter().append("g");

    legend.append("circle")
        .attr("cy", function(d) { return -radius(d); })
        .attr("r", radius);

    legend.append("text")
        .attr("y", function(d) { return -2 * radius(d); })
        .attr("dy", "1.3em")
        .text(d3.format(".1s"));

    // add map
    d3.json("data/provinces-topo-simple.json", function(error, data) {
      map.selectAll('path')
          .data(topojson.feature(data, data.objects['provinces-geo']).features)
        .enter().append('path')
          .attr('class', function(d) { console.log(); return 'province c' + d.properties.code })
          .attr('d', path)
    });

    // add circles
    d3.csv("data/cities.csv", function(data) {
        points.selectAll("circle")
            .data(data)
          .enter().append("circle")
            .attr("cx", function(d) { return projection([d.lon, d.lat])[0]; })
            .attr("cy", function(d) { return projection([d.lon, d.lat])[1]; })
            .attr("r", function(d) { return 10 * Math.sqrt(parseInt(d.pop)); })
            .style("fill", function(d) { return colorScale(d.pop); });

        points.selectAll("text")
            .data(data)
          .enter().append("text")
            .attr("x", function(d) { return projection([d.lon, d.lat])[0]; })
            .attr("y", function(d) { return projection([d.lon, d.lat])[1] + 5; })
            .text(function(d) { return d.name });

    });
    </script>
  </body>
</html>