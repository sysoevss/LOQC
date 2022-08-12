/*
    table must have: create_button, update_button, cancel_button, new_element text field, temp hidden field
*/
function delete_handler(params) {
    $.get('/delete_cycle_object/', { key: params.key, object_type: params.object_type }, function(data) {
        update_table(params.table_id, params.object_type, params.fields, params.click_handler, params.parent_key, params.edit_preload, params.edit_presend);
    });	
}
function update_table(table_id, object_type, fields, click_handler, parent_key, edit_preload = null, edit_presend = null) {
    $("#" + table_id + " tbody").empty();
	$.get('/cycle_objects/', {object_type: object_type, parent_key: parent_key }, function(json) {
        data = JSON.parse(json);
        data.forEach(el => {
            row_str = "<tr>";
            fields.forEach(f => {
                if (f == "name") {
                    row_str += "<td id=" + el[0] + "><a class='loqc_button' href='#'>" + el[1][f] + "</a></td>"
                } else {
                    row_str += "<td>" + el[1][f] + "</td>"
                }
            });
            row_str += "<td>" 
            row_str += "" + "<a id='" + el[0] + "_edit' class='btn-small btn-warning' href='#' title='Edit'><i class='icon-pencil'></i></a>"
            row_str += "" + "<a id='" + el[0] + "_delete' class='btn-small btn-warning' href='#' title='Delete'><i class='icon-trash'></i></a></td>"
            row_str += "</tr>"
            $("#" + table_id + " tbody").append(row_str);
            // delete handler
            $("#" + el[0] + "_delete").click(function(e){
                let current_row = ''; 
                e.preventDefault();
                key = $(this).attr("id");
                key = key.substring(0, key.length - 7);
                params = {key: key, object_type: object_type, table_id: table_id, fields: fields, click_handler: click_handler, parent_key: parent_key, edit_preload: edit_preload, edit_presend: edit_presend}
                confirmation_modal("Please confirm deletion", delete_handler, params = params);
            });
            // edit handler
            $("#" + el[0] + "_edit").click(function(e){
                let current_row = ''; 
                e.preventDefault();
                key = $(this).attr("id");
                if (edit_preload) {
                    edit_preload(key.substring(0, key.length - 5));
                }
                $("#temp_" + table_id).html(key.substring(0, key.length - 5));
                $("#new_element_" + table_id).val(el[1]['name']);
                fields.forEach(f => {
                    if (f != "name") {
                        $("#new_element_" + f + "_" + table_id).val(el[1][f]);
                    }
                });
                $("#create_button_" + table_id).hide();
                $("#update_button_" + table_id).show();
                $("#cancel_button_" + table_id).show();
            }); 
            // click handler
            $("#" + el[0]).click(function(e){
                key = $(this).attr("id");
                click_handler(key);
            });             
        });
	});
}

function init_table(table_id, object_type, fields, click_handler, parent_key, edit_preload = null, edit_presend = null) {
    update_table(table_id, object_type, fields, click_handler, parent_key, edit_preload, edit_presend);
    //
	// Element Creation
	//
	$("#create_button_" + table_id).click(function(e) {
        let element_name = '';
		e.preventDefault();
		element_name = $("#new_element_" + table_id).val();
		if (!element_name) {
		    alert('The name can\'t be empty!');
		    return;
		}
        obj = {name: element_name}
        fields.forEach(f => {
            if (f != "name") {
                obj[f] = $("#new_element_" + f + "_" + table_id).val();
            }
        });
	
		$.post('/add_cycle_object/', {data: JSON.stringify(obj), object_type: object_type, parent_key: parent_key}, function(data) {
            update_table(table_id, object_type, fields, click_handler, parent_key, edit_preload, edit_presend);
			$("#new_element_" + table_id).val("");
            fields.forEach(f => {
                elem = $("#new_element_" + f + "_" + table_id);
                if (elem.prop('type') != 'select-one') {
                    elem.val("");
                }
            });
		});	
    }); 
    //
	// Element Edit
	//
	$("#update_button_" + table_id).click(function(e){
		e.preventDefault();
		element_name = $("#new_element_" + table_id).val();
		if (!element_name) {
		    alert('The name can\'t be empty!');
		    return;
		}
        key = $("#temp_" + table_id).html();
        obj = {name: element_name}
        if (edit_presend) {
            edit_presend();
        }
        fields.forEach(f => {
            if (f != "name") {
                obj[f] = $("#new_element_" + f + "_" + table_id).val();
            }
        });
		$.post('/update_cycle_object/', {key: key, data: JSON.stringify(obj), object_type: object_type}, function(data) {
            update_table(table_id, object_type, fields, click_handler, parent_key, edit_preload, edit_presend);
			$("#new_element_" + table_id).val("");
            fields.forEach(f => {
                elem = $("#new_element_" + f + "_" + table_id);
                if (elem.prop('type') != 'select-one') {
                    elem.val("");
                }
            });            
            $("#create_button_" + table_id).show();
            $("#update_button_" + table_id).hide();
            $("#cancel_button_" + table_id).hide();   
            $("#temp_" + table_id).html("");
		});	        
	});   
    //
	// Cancel Edit
	//
	$("#cancel_button_" + table_id).click(function(e){
        e.preventDefault();
        $("#new_element_" + table_id).val("");
        fields.forEach(f => {
            elem = $("#new_element_" + f + "_" + table_id);
            if (elem.prop('type') != 'select-one') {
                elem.val("");
            }
        });        
        $("#create_button_" + table_id).show();
        $("#update_button_" + table_id).hide();
        $("#cancel_button_" + table_id).hide();   
        $("#temp_" + table_id).html("");
	});		    
}
