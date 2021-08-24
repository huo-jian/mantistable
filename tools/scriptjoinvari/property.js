var fs = require('fs');
 
var it = fs.readFileSync('t2dlima.json', 'utf8').split(',\n');
var prop = fs.readFileSync('property.txt', 'utf8').split('\r\n');
var p = [];
for(var i=0;i<prop.length;i++){
	p[prop[i].toLocaleString()]=true;
}
var arr = [];
for(var i=0;i<it.length;i++){ //
	var a = JSON.parse(it[i]);
	var s = a.neCols;
	for(var j=0;j<s.length;j++){
		if(!(s[j].rel && s[j].rel.substr(0,4)=="http")){
			if(p[s[j].header.toLowerCase()]){
				s[j].rel="http://dbpedia.org/ontology/"+s[j].header;
			}
			
		}
	}
	a.neCols=s;
	arr.push(JSON.stringify(a));
}

fs.appendFile('t2dlimnew.json', arr.join(",\n"), function (err) {
		  if (err) throw err;
		});