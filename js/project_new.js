var probChart;
var fidChart;
$(document).ready(function() {
    if (typeof(localStorage) !== "undefined") {
    }
    
    //
    // LOQC menu
    //
    $(".loqc_menu").click(function(e) {	
		// Show specific container
        $(".loqc_menu_selected").addClass("loqc_menu");
        $(".loqc_menu_selected").removeClass("loqc_menu_selected");
        $(this).addClass("loqc_menu_selected");	
        $("#myprojects_div").hide();
        $("#library_div").hide();
        container_id = $(this).attr("id") + "_div";
        $("#" + container_id).show();	  
    });   

	//
	// Main menu handlers
	//
	$(".nav > li > a").click(function(e) {
	    e.preventDefault();
		
		// Show specific container
        $(".nav > li").removeClass("active");
        $(this).parent().addClass("active");	
        $(".inner").hide();
        container_id = $(this).attr("id") + "_container";
        $("#" + container_id).show();	
	   	
	});
    
    //
    //  Projects table
    //
    function project_click(key) {
        // show controls    
        $("#current_project").show();
        
        // highlight table row
        $(".newspaper-a-selected").removeClass("newspaper-a-selected");
        parent_tr = $("#" + key).parent('tr');
        parent_tr.children().each(function() {
            $(this).addClass("newspaper-a-selected");
        });    

        // set up environment
		$.get('/get_object_by_key/', {object_type: "Project", key: key}, function(json) {
            data = JSON.parse(json);
            $("#current_project_name").html(data["name"]);
            $("#current_project_description").html(data["description"]);
            $("#current_project_key").html(key);
            $("#lo_design_frame").attr("src", "/lo_designer/?id=" + key);
		}); 
        $("#simulate").show();
        $("#simulate_x").show();
        $("#simulate_y").show();
        $("#simulate_z").show();
        $("#matrix_refresh").show();
        $("#fidelity_refresh").show();
        $("#latex_res").html("");
        $("#latex_res").show();
        $("#latex_res_x").html("");
        $("#latex_res_x").show();
        $("#latex_res_y").html("");
        $("#latex_res_y").show();
        $("#latex_res_z").html("");
        $("#latex_res_z").show();
        $("#matrix_res").html("");
        $("#matrix_res").show();
        $("#fidelity_res").html("");
        $("#fidelity_res").show();
        if (probChart) probChart.destroy();
        if (fidChart) fidChart.destroy();
        $("#charts").hide();
    }
    init_table("table_myprojects", "Project", ["name", "description"], project_click, "current_user");
    
    //
    //  Various handlers
    //
    $("#simulate").click(function () {
        $("#simulate").hide();
        $("#latex_res").html("");
        $.get('/simulate/', {project_key: $("#current_project_key").html()}, function(json) {
            $("#simulate").show();
            
            data = JSON.parse(json);
            $("#latex_res").html(data);
            MathJax.typeset();
		});     
    });
    $("#simulate_x").click(function () {
        $("#simulate_x").hide();
        $("#latex_res_x").html("");
        $.get('/simulate_cgate/', {project_key: $("#current_project_key").html(), gate: "X"}, function(json) {
            $("#simulate_x").show();
            
            data = json;
            $("#latex_res_x").html(data);
            MathJax.typeset();
		});     
    });    
    $("#simulate_y").click(function () {
        $("#simulate_y").hide();
        $("#latex_res_y").html("");
        $.get('/simulate_cgate/', {project_key: $("#current_project_key").html(), gate: "Y"}, function(json) {
            $("#simulate_y").show();
            
            data = json;
            $("#latex_res_y").html(data);
            MathJax.typeset();
		});     
    });    
    $("#simulate_z").click(function () {
        $("#simulate_z").hide();
        $("#latex_res_z").html("");
        $.get('/simulate_cgate/', {project_key: $("#current_project_key").html(), gate: "Z"}, function(json) {
            $("#simulate_z").show();
            
            data = json;
            $("#latex_res_z").html(data);
            MathJax.typeset();
		});     
    });    
    $("#matrix_refresh").click(function () {
        $("#matrix_refresh").hide();
        
        $("#matrix_res").html("");
        $.get('/matrices/', {project_key: $("#current_project_key").html()}, function(json) {
            $("#matrix_refresh").show();
            
            data = JSON.parse(json);
            $("#matrix_res").html(data);
            MathJax.typeset();
		});             
    });
    $("#fidelity_refresh").click(function () {
        $("#fidelity_refresh").hide();
        
        if (probChart) probChart.destroy();
        if (fidChart) fidChart.destroy();
        
        $("#fidelity_res").html("");
        $.get('/get_fidelity/', {project_key: $("#current_project_key").html()}, function(json) {
            $("#fidelity_refresh").show();
            res = JSON.parse(json);
            if (res.error == true) {
                $("#fidelity_res").html(res.data);                
                return;
            }
            html_str = "<h4>Gate: " + res.data.gate + "</h4>";
            html_str += "<table class='newspaper-a'><thead><th></th><th>Probabilities:</th><th>Fidelities</th></thead><tbody>";
            html_str += "<tr><td>|00></td><td>" + res.data.p_0[1] + "</td><td>" + res.data.vals_0[1] + "</td></tr>";
            html_str += "<tr><td>|01></td><td>" + res.data.p_0[2] + "</td><td>" + res.data.vals_0[2] + "</td></tr>";
            html_str += "<tr><td>|10></td><td>" + res.data.p_0[3] + "</td><td>" + res.data.vals_0[3] + "</td></tr>";
            html_str += "<tr><td>|11></td><td>" + res.data.p_0[4] + "</td><td>" + res.data.vals_0[4] + "</td></tr>";
            html_str += "<tr><td>|++></td><td>" + res.data.p_0[5] + "</td><td>" + res.data.vals_0[5] + "</td></tr>";
            html_str += "<tr><td>|+-></td><td>" + res.data.p_0[6] + "</td><td>" + res.data.vals_0[6] + "</td></tr>";
            html_str += "<tr><td>|-+></td><td>" + res.data.p_0[7] + "</td><td>" + res.data.vals_0[7] + "</td></tr>";
            html_str += "<tr><td>|--></td><td>" + res.data.p_0[8] + "</td><td>" + res.data.vals_0[8] + "</td></tr>";
            html_str += "<tr><td>|RR></td><td>" + res.data.p_0[9] + "</td><td>" + res.data.vals_0[9] + "</td></tr>";
            html_str += "<tr><td>|RL></td><td>" + res.data.p_0[10] + "</td><td>" + res.data.vals_0[10] + "</td></tr>";
            html_str += "<tr><td>|LR></td><td>" + res.data.p_0[11] + "</td><td>" + res.data.vals_0[11] + "</td></tr>";
            html_str += "<tr><td>|LL></td><td>" + res.data.p_0[12] + "</td><td>" + res.data.vals_0[12] + "</td></tr>";
            html_str += "<tr><td><b>min</b></td><td><b>" + res.data.p_0[0] + "</b></td><td><b>" + res.data.vals_0[0] + "</b></td></tr></tbody></table>";
            $("#fidelity_res").html(html_str);
            
            // charts
            $("#charts").show();
            const prob_data = {
                labels: ["|00>", "|01>", "|10>", "|11>", "|++>", "|+->", "|-+>", "|-->", "|RR>", "|RL>", "|LR>", "|LL>"],
                datasets: [{
                    label: 'precise',
                    data: [res.data.p_0[1], res.data.p_0[2], res.data.p_0[3], res.data.p_0[4],
                           res.data.p_0[5], res.data.p_0[6], res.data.p_0[7], res.data.p_0[8],
                           res.data.p_0[9], res.data.p_0[10], res.data.p_0[11], res.data.p_0[12]],
                    backgroundColor: ['rgba(25, 250, 25, 0.4)'],
                    borderColor: ['rgb(25, 250, 25)'],
                    borderWidth: 1},
                    {label: '1% BS error',
                    data: [res.data.p_1[1], res.data.p_1[2], res.data.p_1[3], res.data.p_1[4],
                           res.data.p_1[5], res.data.p_1[6], res.data.p_1[7], res.data.p_1[8],
                           res.data.p_1[9], res.data.p_1[10], res.data.p_1[11], res.data.p_1[12]],
                    backgroundColor: ['rgba(227, 221, 36, 0.4)'],
                    borderColor: ['rgb(227, 221, 36)'],
                    borderWidth: 1},                    
                    {label: '5% BS error',
                    data: [res.data.p_5[1], res.data.p_5[2], res.data.p_5[3], res.data.p_5[4],
                           res.data.p_5[5], res.data.p_5[6], res.data.p_5[7], res.data.p_5[8],
                           res.data.p_5[9], res.data.p_5[10], res.data.p_5[11], res.data.p_5[12]],
                    backgroundColor: ['rgba(250, 25, 25, 0.4)'],
                    borderColor: ['rgb(250, 25, 25)'],
                    borderWidth: 1},                    
                ]
            };
            const prob_config = {
                type: 'bar',
                data: prob_data,
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                },
            };
            const ctx = $('#probChart');
            probChart = new Chart(ctx, prob_config);

            var items = [
                [-32, -32, -32, -32, -32, -32, -32, -32, -32, -32, -32, -32],
                [-32, -32, -32, -32, -32, -32, -32, -32, -32, -32, -32, -32],
                [-32, -32, -32, -32, -32, -32, -32, -32, -32, -32, -32, -32]
            ];
            for (i = 0; i < 12; i++) {
                if (1 - res.data.vals_0[i+1] > 0) items[0][i] = Math.log10(1 - res.data.vals_0[i+1]);
                if (1 - res.data.vals_1[i+1] > 0) items[1][i] = Math.log10(1 - res.data.vals_1[i+1]);
                if (1 - res.data.vals_5[i+1] > 0) items[2][i] = Math.log10(1 - res.data.vals_5[i+1]);
            }
            const fid_data = {
                labels: ["|00>", "|01>", "|10>", "|11>", "|++>", "|+->", "|-+>", "|-->", "|RR>", "|RL>", "|LR>", "|LL>"],
                datasets: [{
                    label: 'precise',
                    data: items[0],
                    backgroundColor: ['rgba(25, 250, 25, 0.4)'],
                    borderColor: ['rgb(25, 250, 25)'],
                    borderWidth: 1},
                    {label: '1% BS error',
                    data: items[1],
                    backgroundColor: ['rgba(227, 221, 36, 0.4)'],
                    borderColor: ['rgb(227, 221, 36)'],
                    borderWidth: 1},                    
                    {label: '5% BS error',
                    data: items[2],
                    backgroundColor: ['rgba(250, 25, 25, 0.4)'],
                    borderColor: ['rgb(250, 25, 25)'],
                    borderWidth: 1},                    
                ]
            };
            const fid_config = {
                type: 'bar',
                data: fid_data,
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                },
            };
            const ctx1 = $('#fidChart');
            fidChart = new Chart(ctx1, fid_config);   
		});             
    });    

    //
    //  Library
    //
    refresh_lib();
    $("#copy").click(function () {
        $.get('/copy_project/', {key: $("#lib_project_key").html()}, function(json) {
            update_table("table_myprojects", "Project", ["name", "description"], project_click, "current_user");
            alert(json);
		});     
    });
    
    //
    //  Top menu
    //
    $(document).on('click', ".top_menu", function(e) {
        $(".top_menu_selected").addClass("top_menu");
        $(".top_menu_selected").removeClass("top_menu_selected");
        $(this).addClass("top_menu_selected");
        $(this).removeClass("top_menu");
        
        $(".top_menu_container").hide();
        container_id = $(this).attr("id") + "_container";
        $("#" + container_id).show();	          
    });
    $(document).on('click', ".top_menu_selected", function(e) {
        $(".top_menu_selected").removeClass("top_menu_selected");
        $(this).addClass("top_menu");
        
        $(".top_menu_container").hide();
    });
    
	// after everything is loaded, display the page
	$("#all_content").show();       
});



//
//
//
//		FUNCTIONS
//
//
//
//
//
//
//
function refresh_lib() {
    $.get('/get_library/', {}, function(json) {
        $("#table_lib_projects tbody").html("");
        lib_html = "";
        data = JSON.parse(json);
        data.forEach(el => {
            lib_html += "<tr onclick='display_lib_project(\"" + el.key + "\");'><td style='background-color: rgba(0, 100, 180, 0.3);'>" + el.name + "</td><td>" + el.descr + "</td><td>" + el.user + "</td></tr>";             
        });           
        $("#table_lib_projects tbody").html(lib_html);            
        $("#lib_project_name").hide();
        $("#lib_project_key").html("");
        $("#lib_project_description").hide();
        $("#lib_pic_container").hide();
        $("#copy").hide();
    });         
}
function display_lib_project(key) {    
    $.get('/get_object_by_key/', {object_type: "Project", key: key}, function(json) {
        data = JSON.parse(json);
        $("#lib_project_name").html(data["name"]);
        $("#lib_project_name").show();
        $("#lib_project_key").html(key);
        $("#lib_project_description").html(data["description"]);
        $("#lib_project_description").show();

        $("#project_picture").attr("src", data["png"]);
        $("#lib_pic_container").show();
        $("#copy").show();
    }); 
}
function getDataUri(url, callback) {
    var image = new Image();

    image.onload = function () {
        var canvas = document.createElement('canvas');
        canvas.width = this.naturalWidth; // or 'width' if you want a special/scaled size
        canvas.height = this.naturalHeight; // or 'height' if you want a special/scaled size

        width = canvas.width;
        height = canvas.height;
        if (width > 500) {
            width = 500;
            height = Math.floor(height / (width / 500));
        }
        canvas.getContext('2d').drawImage(this, 0, 0, width, height);

        // Get raw image data
        callback(canvas.toDataURL('image/png').replace(/^data:image\/(png|jpg);base64,/, ''));

        // ... or get as Data URI
        callback(canvas.toDataURL('image/png'));
    };

    image.src = url;
}

function show_image_modal(src, title) {
	var $imageSrc = $(this);
  	var $imageSrcAttr = $imageSrc.attr('href');
  	var $linkTitle = $(this);
  	var $linkTitleAttr = $imageSrc.attr('title');
  
  	var $dialog = $('<div class="image-container"><img src="' + src + '" /><div>').dialog({
  		width: 1000,
  		autoOpen: false,
  		position: { my: "left top", at: "left bottom", of: $("#nav_container") },
  		modal: true,
  		title: title,
        closeText: "X",        
  		// start animation
  		show: {
  			effect: "blind",
  			duration: 100
  		},
  		hide: {
  			effect: "blind",
  			duration: 100
  		},
  		// end animation
  	}); 
  	$dialog.dialog('open');
}

function show_page_modal(url, title) {
    var $dialog = $($('<div class="image-container"></div>').load(url)).dialog({
	width: 1000,
	autoOpen: false,
	position: {my: "left top", at: "left bottom", of: $("#nav_container")},
	modal: true,
	title: title,
	closeText: "X",
	show: {
	    effect: "blind",
	    duration: 100
	},
	hide: {
	    effect: "blind",
	    duration: 100
	}
    });
    $dialog.dialog('open');
}

function confirmation_modal(question, handler, params = null) {    
    // clean form
    $("#confirmation_template").html(question);
    
    // dialog
    var dialog = $('#confirmation_template').dialog({
	width: 700,
	autoOpen: false,
	modal: true,
    zIndex: 9998,
    stack: false,
	title: "Confirm action",
	closeText: "X",
	show: {
	    effect: "blind",
	    duration: 100
	},
	hide: {
	    effect: "blind",
	    duration: 100
	},
    buttons: {
        "Confirm": function () {
            if (params)
                handler(params);
            else
                handler();
            dialog.dialog( "close" );
        },
        "Cancel": function() {
          dialog.dialog( "close" );
        }
    },    
    close: function() {
        
    }    
    });
    dialog.dialog('open');
}
