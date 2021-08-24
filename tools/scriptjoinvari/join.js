var fs = require('fs');
 
var it = fs.readFileSync('errorTables.json', 'utf8').split('\n');
var an = fs.readFileSync('annotation3.json', 'utf8').split('\n');
var itable = [];
for(var i =0;i<it.length;i++){
	var tmp = JSON.parse(it[i]);
	itable[tmp.table_id]=tmp.table_name;
}
for(var i =0;i<an.length-1;i++){
	var tmp = JSON.parse(an[i]);
	itable[tmp.table_id]=false;
}
for(var ita in itable){
	if(itable[ita]!=false)
		console.log(itable[ita]);
}
//console.log(itable);