getDataService();


function getDataService() {
    chartsMaker(result.Charts);
    appsMaker(result.Applications);
    nodeMaker(result.Nodes);
}

function appsMaker(apps) {
    let html = " <div class=\"cell small-12 apps-section-title text-center \"> Applications </div>";

    for (let i = 0; i < apps.length; i++) {
        let app = "<div class=\"cell small-10 medium-6 large-3 float-center\">\n" +
            "                <div class=\"apps-card\" id=\"apps-card-1\">\n" +
            "                    <div class=\"x-slide\">\n" +
            "                        <div class=\"simple-slider simple-slider-" + i + "\">\n" +
            "                            <div class=\"slider-wrapper\">\n";
        let images = apps[i].Images;
        let str = "";
        for (let j = 0; j < images.length; j++) {
            str += " <div class=\"slider-slide\" style=\"background-image: url('" + images[j] + "')\">\n" +
                "                                    &nbsp;\n" +
                "                                </div>";
        }

        app += str + "</div>";
        app += "                            <div class=\"slider-btn slider-btn-prev\"><img src='assets/photo/left_round_32px.png' alt=''></div>\n" +
            "                            <div class=\"slider-btn slider-btn-next\"><img src='assets/photo/left_round_32px-next.png' alt=''></div>\n" +
            "                        </div>\n" +
            "                    </div>\n" +
            "\n" +
            "                    <div class=\"name text-center\">" + apps[i].Name + "</div>\n" +

            "<div class='text-center float-center sponsorship'>Sponsorships</div>" +
            "                    <div class=\"number\">\n" +
            "                        <div class=\"assigned \">\n" +
            "                            <div class=\"as-title \">Assigned</div>\n" +
            "                            <div class=\"sponsorship-desc  text-center\">" + apps[i]["Assigned Sponsorships"] + "</div>\n" +
            "                        </div>\n" +
            "                        <div class=\"assigned \">\n" +
            "                            <div class=\"sponsorship-title \">&nbsp;   Unused &nbsp;</div>\n" +
            "                            <div class=\"sponsorship-desc text-center\">" + apps[i]["Unused Sponsorships"] + "</div>\n" +
            "                        </div>\n" +
            "                    </div>\n" +
            "\n" +
            "                    <div class=\"context\">\n" +
            "                        <div class=\"desc\">" + apps[i].Context + "</div>\n" +
            "                    </div>\n" +
            "                    <div class=\"description\">\n" +
            "                        <div class=\"title\">About Us</div>\n" +
            "                        <div class=\"desc\">" + apps[i].Description + "</div>\n" +
            "                    </div>\n" +
            "                    <div class=\"testimonial\">\n" +
            "                        <div class=\"desc\"> " + apps[i].Testimonial + "</div>\n" +
            "                    </div>\n" +
            "                    <div class=\"links\">\n" +
            "                        <div class=\"desc\">\n";
        str = "";
        links = apps[i].Links;
        for (let j = 0; j < links.length; j++) {
            str += "<a class=\"link-item\"  target='_blank' href=\"" + links[j] + "\">" + links[j] + "</a>\n";
        }
        app += str + "                        </div>\n" +
            "\n" +
            "                    </div>\n" +
            "                </div>\n" +
            "            </div>";
        html += app;
    }
    $("#apps").html(html);
    let sliderArr = [];
    for (let i = 0; i < apps.length; i++) {
        sliderArr[i] = new SimpleSlider('.simple-slider-' + i, {speed: 500})
    }
}


function nodeMaker(nodes) {
    let html = " <div class=\"cell small-12 node-section-title text-center \"> Nodes </div>";
    for (let i = 0; i < nodes.length; i++) {
        node = "    <div class=\"cell small-10 medium-6 large-3\">\n" +
            "        <div class=\"node-card\">\n" +
            "            <div class=\"logo-img\">\n" +
            "                <img src=\"\" alt=\"\">\n" +
            "            </div>\n" +
            "            <div class=\"name node-name text-center\">" + nodes[i].Name + "</div>\n" +
            "\n" +
            "            <div class=\"address\">\n" +
            "                <div class=\"title\">Address</div>\n" +
            "                <div class=\"desc\">" + nodes[i].Address + "</div>\n" +
            "            </div>\n" +
            "            <div class=\"testimonial\">\n" +
            "                <div class=\"title\">About Us</div>\n" +
            "                <div class=\"desc\"> " + nodes[i].Testimonial + "</div>\n" +
            "            </div>\n" +
            "            <div class=\"links\">\n" +
            "                <div class=\"desc\">";
        str = "";
        links = nodes[i].Links;
        for (let j = 0; j < links.length; j++) {
            str += "<a class=\"link-item\" target='_blank' href=\"" + links[j] + "\">" + links[j] + "</a>\n";
        }
        node += str + "</div>\n" +
            "\n" +
            "            </div>\n" +
            "        </div>\n" +
            "    </div>    ";
        html += node;
    }
    $("#nodes").html(html);
}


function chartsMaker(charts) {

    let html = "";
    for (let i = 0; i < charts.length; i++) {
        let chart = "<div class=\"cell small-12 medium-6 large-4 chart-card\">" +
            "<div class='title-chart text-center'>" + charts[i].title + "</div>" +
            " <canvas class='' id=\"chart-" + i + "\">chart</canvas></div>" + "\n";
        html += chart;
    }
    $("#charts").html(html);

    for (let i = 0; i < charts.length; i++) {
        let step_size = 1;
        if (i === 0) {
            step_size = 5;
        }
        charTools(document.getElementById('chart-' + i).getContext('2d'), charts[i].timestamps, charts[i].values, step_size);
    }
}

function charTools(ctx,
                   data_label,
                   data_value,
                   step_size) {
    background_color = '#232020';
    border_color = '#ed795d';
    border_width = 4
    let chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data_label,
            datasets: [{
                fill: false,
                backgroundColor: background_color,
                borderColor: border_color,
                borderWidth: border_width,
                data: data_value,
            }]
        },
        options: {
            layout: {
                padding: {
                    left: -5,
                    right: 10,
                    top: 10,
                    bottom: 0
                }
            },
            legend: {
                display: false
            },
            tooltips: {
                enabled: false
            },
            elements: {},
            scales: {
                yAxes: [{
                    ticks: {
                        stepSize: step_size,
                        display: true,
                        beginAtZero: true
                    },
                    gridLines: {
                        display: true,
                        drawBorder: false
                    }
                }],
                xAxes: [{
                    ticks: {
                        stepSize: 5,
                        display: false,
                        beginAtZero: true
                    },
                    gridLines: {
                        display: true,
                        drawBorder: false
                    }
                }],
            }
        }
    });
}