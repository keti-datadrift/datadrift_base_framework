<!DOCTYPE html>
<html>
<head>
	<meta charset="utf-8">
	<style>
		@import url(http://fonts.googleapis.com/earlyaccess/nanumgothic.css);
		text, div, h1, h3, span { 
			font-family: 'Nanum Gothic', sans-serif; 
			font-size: 13px;
		}
		.background {
			fill: #fff;
		}
		.province {
			fill: #eee;
			stroke: #555;
			stroke-width: 1;
			fill-opacity: 0.1;
			stroke-opacity: 0.5;
		}
		.precinct {
			stroke: #fff;
			stroke-width: 1;
			opacity: 0.5;
		}
		.province-label {
			font-size: 10px;
			text-anchor: middle;
			fill: #333; 
		}
		.precinct-label {
			font-size: 3px;
			text-anchor: middle;
			visibility: hidden;
		}
		.g_precincts {
			pointer-events: all;
		}
		.province.highlighted {
			fill-opacity: 0.01;
			stroke-opacity: 0.9;			
		}
		.precinct.highlighted {
			opacity: 0.8;			
		}
		.province.notselected {
			fill-opacity: 0.5;
		}
		.province.selected {
			fill: none;
			stroke: #555;
			stroke-opacity: 1.0;
			opacity: 1.0;
		}
		.precinct.selected {
			stroke: #555;
			stroke-opacity: 1.0;
			opacity: 0.7;
		}
		#info {
			position: absolute;
			top: 0;
			left: 0;
			padding: 5px;
			width: 160px;
			height: 95px;
			background-color: #333;
			color: white;
			visibility: hidden;
		}
		#info h3 {
			margin: 0 0 8px 0;
			padding: 0 0 1px 0;
			font-size: 14px;
			border-bottom: 1px solid #eee;
		}
		#info div {
			float: left;
		}
		img {
			height: 65px;
			margin: 0 5px 0 0;
			float: left;
		}
	</style>
</head>
<body>

<svg></svg>

<div id="info">
</div>

<script src="http://d3js.org/d3.v3.min.js"></script>
<script src="http://d3js.org/topojson.v1.min.js"></script>
<script>
	var maps_path = {19: {"provinces": "data/provinces-topo.json", "precinct": "data/assembly-precinct-19-topo-simplified.json"}}
	var topo_key = {19: {"provinces": "provinces-geo", "precinct": "precincts"}}

	var assembly_no = 19;

	var width = 960, height = 720;
	var active = d3.select(null);
	
	var proj = d3.geo.mercator()
		.center([128.0, 35.9])
		.scale(6000)
		.translate([width/2, height/2]);

	var path = d3.geo.path()
		.projection(proj);

	var svg = d3.select("svg")
		.attr("width", width)
		.attr("height", height);
	
	svg.append("rect")
		.attr("class", "background")
		.attr("width", width)
		.attr("height", height)
		.on("click", reset);

	var g = svg.append("g");

	var precinct_person = {}; 
	
	d3.json("data/precinct_person.json", function(error, data) {
		precinct_person = data.precincts;
	});

	var gm = g.append("g");
	var gp = g.append("g");
	
	d3.json(maps_path[assembly_no]["provinces"], function(error, kor) {
		var provinces = topojson.feature(kor, kor.objects[topo_key[assembly_no]["provinces"]]);
		
		var g_provinces = gp.selectAll('g')
			.data(provinces.features, function(d) { return d.properties.code; })
			.enter()
			.append('g')
			.attr('class', 'g_province');
		
		g_provinces.append('path')
			.attr('d', path)
			.attr('class', 'province')
			.on("click", clicked)
			.append("title")
			.text(function(d) { return d.properties.name; });

		g_provinces.append("text")
			.attr("class", "province-label")
			.attr("id", function(d) { return "subunit-label " + d.properties.code; })
			.attr("transform", function(d) { return "translate(" + path.centroid(d) + ")"; })
			.attr("dy", ".35em")
			.text(function(d) { return d.properties.name; });

		g_provinces.on("mouseover", function() {
			d3.select(this).select("path").classed("highlighted", true);
		});
		g_provinces.on("mouseout", function() {
			d3.select(this).select("path").classed("highlighted", false);
		})
	});

	d3.json(maps_path[assembly_no]["precinct"], function(error, kor) {
		var precincts = topojson.feature(kor, kor.objects[topo_key[assembly_no]["precinct"]]);
		
		var g_precincts = gm.selectAll('g')
			.data(precincts.features, function(d) { return d.properties.precinct_no; })
			.enter()
			.append('g')
			.attr('class', 'g_precinct');
		
		g_precincts
			.append('path')
			.attr('d', path)
			.attr('class', 'precinct')
			.append("title")
			.text(function(d) { return d.properties.precinct_name; });

		g_precincts.append("text")
			.attr("class", "precinct-label")
			.attr("transform", function(d) { return "translate(" + path.centroid(d) + ")"; })
			.attr("dy", ".35em")
			.text(function(d) { return d.properties.precinct_name; });
		
		g_precincts.select("path.precinct")
			.style("fill", function(d) {
				if( precinct_person.hasOwnProperty(+d.properties.precinct_no) ) {
					return precinct_person[+d.properties.precinct_no].party_color;
				}
				else {
					return "#999999";
				}
			})
			

		g_precincts.on("mouseover", function() {
			d3.select(this).select("path").classed("highlighted", true);
			
			var precinct_code = d3.select(this).datum().properties.precinct_no;
			var html_text = "";
			
			if( precinct_person.hasOwnProperty(precinct_code) ) {
				var precinct = precinct_person[precinct_code];
				html_text += '<h3>'+precinct.precinct_name+'</h3>';
				html_text += '<img src="'+precinct.image+'" />';
				html_text += '<div>' + precinct.person_name + '<br /><span style="color: white; background-color: '+precinct.party_color+';">'+ precinct.party + '</span></div>';
			}
			else {
				html_text = "No data"
			}

			var point = d3.mouse(this);
			d3.select("#info")
				.style("left", function(d) { return point[0]+"px"; })
				.style("top", function(d) { return point[1]+"px"; })
				.style("visibility", "visible")
				.html(html_text);
		});
		g_precincts.on("mouseout", function() {
			d3.select(this).select("path").classed("highlighted", false);
			d3.select("#info")
				.style("visibility", "hidden");
		})

	});

function clicked(d) {
	if (active.node() === this) return reset();
	active.classed("active", false);
	active = d3.select(this).classed("active", true);

	var bounds = path.bounds(d),
			dx = bounds[1][0] - bounds[0][0],
			dy = bounds[1][1] - bounds[0][1],
			x = (bounds[0][0] + bounds[1][0]) / 2,
			y = (bounds[0][1] + bounds[1][1]) / 2,
			scale = .7 / Math.max(dx / width, dy / height),
			translate = [width / 2 - scale * x, height / 2 - scale * y];

	g.transition()
			.duration(750)
			.style("stroke-width", 1.5 / scale + "px")
			.attr("transform", "translate(" + translate + ")scale(" + scale + ")");
	
	d3.selectAll(".province").classed("selected", false);
	d3.selectAll(".province").classed("notselected", false);
	d3.selectAll(".precinct").classed("selected", false);
	d3.selectAll("text.precinct-label").style("visibility", "hidden");
	
	d3.selectAll(".province").style("stroke-width", 2 / scale + "px");
	d3.selectAll(".precinct").style("stroke-width", 1 / scale + "px");
	
	d3.selectAll("text.province-label").style("font-size", 14 / scale + "px");

	
	if( d3.select(this).classed("province") ) {
		d3.selectAll(".province").classed("notselected", true);
		d3.select(this).classed("notselected", false);
		d3.select(this).classed("selected", true);
		d3.selectAll("text.precinct-label")
			.filter(function(d2) { 
				if( precinct_person.hasOwnProperty(+d2.properties.precinct_no) ) { 
					return d.properties.code == precinct_person[+d2.properties.precinct_no].province_code; 
				} 
				else false; 
			})
			.style("visibility", "visible")
			.style("font-size", 10 / scale + "px");
	}
}

function reset() {
	active.classed("active", false);
	active = d3.select(null);

	g.transition()
			.duration(750)
			.style("stroke-width", "1.5px")
			.attr("transform", "");

	d3.selectAll(".province").classed("selected", false);
	d3.selectAll(".province").classed("notselected", false);
	d3.selectAll(".precinct").classed("selected", false);
	d3.selectAll("text.precinct-label").style("visibility", "hidden");
	d3.selectAll("text.province-label").style("font-size", "10px");
}

</script>

</body>
</html>