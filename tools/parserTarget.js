let fs = require('fs');
let files = ['CTA_Round2_Targets.csv', 'CPA_Round2_Targets.csv', 'CEA_Round2_Targets.csv'];

let lines = fs.readFileSync(files[0]).toString().trim().split('\n');
let result = parsingCTATarget(lines);
fs.writeFileSync('CTATarget.json', JSON.stringify([...result], null, 4));

lines = fs.readFileSync(files[1]).toString().trim().split('\n');
result = parsingCPATarget(lines);
fs.writeFileSync('CPATarget.json', JSON.stringify([...result], null, 4));

lines = fs.readFileSync(files[2]).toString().trim().split('\n');
result = parsingCEATarget(lines);
fs.writeFileSync('CEATarget.json', JSON.stringify(result, null, 4));

function parsingCTATarget(lines) {
  let result = new Map();
  for(let line of lines) {
    let tmp = line.substring(1, line.length-1).split('","');
    if(!result.get(tmp[0])) {
      result.set(tmp[0], []);
    }
    let array = result.get(tmp[0]);
    array.push(tmp[1]);  
  }
  return result;
}

function parsingCPATarget(lines) {
  let result = new Map();
  for(let line of lines) {
    let tmp = line.substring(1, line.length-1).split('","');
    if(!result.get(tmp[0])) {
      result.set(tmp[0], []);
    }
    let array = result.get(tmp[0]);
    array.push(tmp[2]);  
  }
  return result;
}

function parsingCEATarget(lines) {
  let result = {};
  for(let line of lines) {
    let tmp = line.substring(1, line.length-1).split('","');
    if(!result[tmp[0]]) {
      result[tmp[0]] = {};
    }
    let map = result[tmp[0]];
    if(!map[tmp[1]]) {
      map[tmp[1]] = [];
    }
    let array = map[tmp[1]];
    array.push(tmp[2]);  
  }
  return result;
}
