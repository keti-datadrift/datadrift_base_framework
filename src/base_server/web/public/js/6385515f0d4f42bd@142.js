function _1(md){return(
md`<div style="color: grey; font: 13px/25.5px var(--sans-serif); text-transform: uppercase;"><h1 style="display: none;">Global temperature trends</h1><a href="https://d3js.org/">D3</a> › <a href="/@d3/gallery">Gallery</a></div>

# Global temperature trends

Based on [“How 2016 Became Earth’s Hottest Year on Record”](https://www.nytimes.com/interactive/2017/01/18/science/earth/2016-hottest-year-on-record.html) by Jugal K. Patel. Data: [NASA Goddard Institute for Space Studies](https://data.giss.nasa.gov/gistemp/)`
)}

function _chart(d3,data)
{
  const width = 928;
  const height = 600;
  const marginTop = 20;
  const marginRight = 30;
  const marginBottom = 30;
  const marginLeft = 40;

  const x = d3.scaleUtc()
      .domain(d3.extent(data, d => d.date))
      .range([marginLeft, width - marginRight]);

  const y = d3.scaleLinear()
      .domain(d3.extent(data, d => d.value)).nice()
      .range([height - marginBottom, marginTop]);

  const max = d3.max(data, d => Math.abs(d.value));

  // Create a symmetric diverging color scale.
  const color = d3.scaleSequential()
      .domain([max, -max])
      .interpolator(d3.interpolateRdBu);

  const svg = d3.create("svg")
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height])
      .attr("style", "max-width: 100%; height: auto;");

  svg.append("g")
      .attr("transform", `translate(0,${height - marginBottom})`)
      .call(d3.axisBottom(x).ticks(width / 80))
      .call(g => g.select(".domain").remove());

  svg.append("g")
      .attr("transform", `translate(${marginLeft},0)`)
      .call(d3.axisLeft(y).ticks(null, "+"))
      .call(g => g.select(".domain").remove())
      .call(g => g.selectAll(".tick line")
        .clone()
          .attr("x2", width - marginRight - marginLeft)
          .attr("stroke-opacity", d => d === 0 ? 1 : 0.1))
      .call(g => g.append("text")
          .attr("fill", "#000")
          .attr("x", 5)
          .attr("y", marginTop)
          .attr("dy", "0.32em")
          .attr("text-anchor", "start")
          .attr("font-weight", "bold")
          .text("Anomaly (°C)"));

  svg.append("g")
      .attr("stroke", "#000")
      .attr("stroke-opacity", 0.2)
    .selectAll()
    .data(data)
    .join("circle")
      .attr("cx", d => x(d.date))
      .attr("cy", d => y(d.value))
      .attr("fill", d => color(d.value))
      .attr("r", 2.5);

  return svg.node();
}


async function _data(d3,FileAttachment)
{
  const data = [];
  // https://data.giss.nasa.gov/gistemp/tabledata_v3/GLB.Ts+dSST.csv
  await d3.csvParse(await FileAttachment("temperatures.csv").text(), (d, i, columns) => {
    for (let i = 1; i < 13; ++i) { // pivot longer
      data.push({date: new Date(Date.UTC(d.Year, i - 1, 1)), value: +d[columns[i]]});
    }
  });
  return data;
}


export default function define(runtime, observer) {
  const main = runtime.module();
  function toString() { return this.url; }
  const fileAttachments = new Map([
    ["temperatures.csv", {url: new URL("./files/a6f8018172231770fcb74b515ac8f7d1e40f466f22190c2e89f7621087b4b02a21e5e9a7f20ccb9563055aa1ed16d95b448e7e6dc6d5e7bd096a72a4de0f002d.csv", import.meta.url), mimeType: "text/csv", toString}]
  ]);
  main.builtin("FileAttachment", runtime.fileAttachments(name => fileAttachments.get(name)));
  main.variable(observer()).define(["md"], _1);
  main.variable(observer("chart")).define("chart", ["d3","data"], _chart);
  main.variable(observer("data")).define("data", ["d3","FileAttachment"], _data);
  return main;
}
