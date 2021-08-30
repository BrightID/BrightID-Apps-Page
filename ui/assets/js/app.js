$(document).ready(function() {
  $.get("apps.json", function(data) {
    chartsMaker(data.Charts);
    appsMaker(data.Applications);
    nodeMaker(data.Nodes);
  });
  if (window.innerWidth < 900) {
    $(".cell").addClass("float-center");
    $("#topbar-center-logo").height("120px");
  } else {
    chartsHeight = $(".wrapper-charts").height();
    $(".chart-spanner").height((window.innerHeight - chartsHeight) / 2 + "px");
  }
});

function appsMaker(apps) {
  html = apps.map(app => {
    if (!app.Testing) {
      let link = app.Links.map(link => (`<a class="link-item" target="_blank" href="${link}">${link}</a>`));
      let elem = `
        <div class="cell small-10 medium-6 large-3">
          <div class="apps-card" id="apps-card-1">
            <div class="img-wrapper">
              <a target="_blank" href="${app.Links[0]}">
                <img class="img-logo" src="${app.Images[0]}">
              </a>
            </div>
            <div class="name-wrapper">
              <div class="name text-center">${app.Name}</div>
            </div>
            <div class="text-center float-center sponsorship">Sponsorships</div>
            <div class="number">
              <div class="assigned ">
                <div class="as-title ">Assigned</div>
                <div class="sponsorship-desc text-center">
                  <p>${app["Assigned Sponsorships"]}</p>
                </div>
              </div>
              <div class="assigned">
                <div class="sponsorship-title">&nbsp; Used &nbsp;</div>
                <div class="sponsorship-desc text-center">
                  <p>${app["Assigned Sponsorships"] - app["Unused Sponsorships"]}</p>
                </div>
              </div>
              <div class="assigned">
                <div class="sponsorship-title">&nbsp;Verified users &nbsp;</div>
                <div class="sponsorship-desc text-center">
                  <p>${app["users"]}</p>
                </div>
              </div>
            </div>
            <div class="context">
            <div class="title">Context: </div>
              <div class="desc-ctx">${app.Context}</div>
            </div>
            <div class="description">
              <div class="desc">${app.Description}</div>
            </div>
            <div class="testimonial">
              <div class="desc"> ${app.Testimonial}</div>
            </div>
            <div class="links">
              <div class="desc">
                ${link.join("")}
              </div>
            </div>
          </div>
        </div>\n`;
      return elem;
    }
  })
  $("#apps").html(html.join(""));
}

function nodeMaker(nodes) {
  let html = '<div class="cell small-12 node-section-title text-center"> Nodes </div>';
  nodesHtml = nodes.map(node => {
    links = node.Links.map(link => (`<a class="link-item" target="_blank" href="${link}">${link}</a>`));
    nodeItem = `
      <div class="cell small-10 medium-6 large-3">
      <div class="node-card">
      <div class="img-wrapper">
        <a target="_blank" href="${node.Links[0]}">
          <img class="img-logo" src="${node.Images[0]}">
        </a>
      </div>
        <div class="name text-center">${node.Name}</div>
        <div class="address">
          <div class="title">Node Address:</div>
          <div class="desc-addr">${node.Address}</div>
        </div>
        <div class="signing-key">
          <div class="title">Node public signing key:</div>
          <div class="desc-signing-key">${node['Public Signing Key'] || '__'}</div>
        </div>
        <div class="signing-key">
        </div>
        <div class="testimonial">
          <div class="desc"> ${node.Testimonial}</div>
        </div>
        <div class="links">
          <div class="desc">
            ${links.join("")}
          </div>
        </div>
      </div>
    </div>`;
    return nodeItem;
  })
  $("#nodes").html(html + nodesHtml.join(""));
}

function chartsMaker(charts) {
  let html = "";
  for (let i = 0; i < charts.length; i++) {
    let chart =
      '<div class="cell small-12 medium-6 large-4 chart-card">' +
      "<div class='title-chart text-center'>" +
      charts[i].title +
      "</div>" +
      " <canvas class='' id=\"chart-" +
      i +
      '">chart</canvas></div>' +
      "\n";
    html += chart;
  }
  $("#charts").html(html);
  for (let i = 0; i < charts.length; i++) {
    let step_size = 1;
    if (i === 0) {
      step_size = Math.ceil((Math.max(...charts[i].values) / 6) / 100) * 100;
    }
    if (i === 1) {
      step_size = Math.ceil(Math.max(...charts[i].values) / 6);
    }
    charTools(
      document.getElementById("chart-" + i).getContext("2d"),
      charts[i].timestamps,
      charts[i].values,
      step_size
    );
  }
}

function convertDate(ts) {
  var date_ob = new Date(ts * 1000);
  let month = date_ob.toLocaleString('default', { month: 'short' });
  let date = date_ob.getDate();
  return `${month}`;
}

function charTools(ctx, data_label, data_value, step_size) {
  background_color = "#232020";
  border_color = "#ed795d";
  border_width = 4;
  fmtLabel = [];
  for (let i = 0; i < data_label.length; i++) {
    if (data_label[i] == '') {
      fmtLabel.push('');
    } else {
      fmtLabel.push(convertDate(data_label[i]));
    }
  }
  let chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: fmtLabel,
      datasets: [{
        lineTension: false,
        fill: false,
        backgroundColor: background_color,
        borderColor: border_color,
        borderWidth: border_width,
        data: data_value,
      }],
    },
    options: {
      layout: {
        padding: {
          left: -5,
          right: 10,
          top: 10,
          bottom: 0,
        },
      },
      legend: {
        display: false,
      },
      tooltips: {
        enabled: false,
      },
      elements: {},
      scales: {
        yAxes: [{
          ticks: {
            stepSize: step_size,
            display: true,
            beginAtZero: true,
          },
          gridLines: {
            display: true,
            drawBorder: false,
          },
        }],
        xAxes: [{
          ticks: {
            stepSize: 5,
            display: true,
            // beginAtZero: true,
            autoSkip: false,
            maxRotation: 45,
            minRotation: 45
          },
          gridLines: {
            display: false,
            drawBorder: false,
          },
        }],
      },
    },
  });
}