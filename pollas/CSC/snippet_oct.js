(function(){
  /* CSC OCTAVOS MIXTO+120'. CUPO = nº de ANDRES BORRERO (1..5). Cambia y re-pega. NO envía. */
  var CUPO = 4;  // <<<<<< 4=ancla(B4) · 1,2=defensivas · 3,5=lotería
  var PART = [{"L": "Canadá", "V": "Marruecos", "aL": ["canada"], "aV": ["marruecos", "morocco"], "s": [[1, 2], [1, 2], [1, 3], [1, 2], [0, 2]]}, {"L": "Paraguay", "V": "Francia", "aL": ["paraguay"], "aV": ["francia", "france"], "s": [[1, 3], [1, 3], [1, 3], [1, 2], [0, 2]]}, {"L": "Brasil", "V": "Norway", "aL": ["brasil", "brazil"], "aV": ["noruega", "norway"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [1, 1]]}, {"L": "México", "V": "Inglaterra", "aL": ["mexico"], "aV": ["inglaterra", "england"], "s": [[1, 1], [1, 1], [1, 1], [1, 2], [2, 1]]}, {"L": "Portugal", "V": "España", "aL": ["portugal"], "aV": ["espana", "spain"], "s": [[1, 2], [1, 2], [1, 3], [1, 2], [1, 1]]}, {"L": "USA", "V": "Bélgica", "aL": ["usa", "estadosunidos", "unitedstates", "eeuu"], "aV": ["belgica", "belgium"], "s": [[1, 2], [2, 1], [2, 1], [1, 2], [1, 1]]}, {"L": "Argentina", "V": "Egipto", "aL": ["argentina"], "aV": ["egipto", "egypt"], "s": [[2, 1], [2, 1], [2, 0], [2, 1], [3, 1]]}, {"L": "Suiza", "V": "Colombia", "aL": ["suiza", "switzerland"], "aV": ["colombia"], "s": [[1, 2], [1, 2], [1, 1], [1, 2], [2, 1]]}];
  function k(s){return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z]/g,"");}
  function has(t,al){for(var i=0;i<al.length;i++){if(t.indexOf(al[i])>=0)return t.indexOf(al[i]);}return -1;}
  function setVal(el,v){el.value=v;["input","change","blur"].forEach(function(ev){el.dispatchEvent(new Event(ev,{bubbles:true}));});}
  var inputs=[].slice.call(document.querySelectorAll("input[type=number],input[type=text],input:not([type])"));
  var conts=[],seen=[];
  inputs.forEach(function(inp){var n=inp;for(var u=0;u<7&&n;u++){n=n.parentElement;if(!n)break;
    if(n.querySelectorAll("input[type=number],input[type=text],input:not([type])").length>=2){if(seen.indexOf(n)<0){seen.push(n);conts.push(n);}break;}}});
  var ok=0,miss=[];
  PART.forEach(function(p){var done=false;
    for(var c=0;c<conts.length;c++){var t=k(conts[c].textContent);var iL=has(t,p.aL),iV=has(t,p.aV);
      if(iL>=0&&iV>=0){var ins=conts[c].querySelectorAll("input[type=number],input[type=text],input:not([type])");if(ins.length<2)continue;
        var rev=iV<iL,gl=p.s[CUPO-1][0],gv=p.s[CUPO-1][1];setVal(ins[0],rev?gv:gl);setVal(ins[1],rev?gl:gv);ok++;done=true;break;}}
    if(!done)miss.push(p.L+" vs "+p.V);});
  console.log("%cCSC ANDRES BORRERO "+CUPO+": llené "+ok+"/"+PART.length,"font-size:14px;color:"+(ok==PART.length?"green":"orange"));
  if(miss.length)console.warn("FALTAN (a mano):",miss);
  console.log("Revisa y dale ENVIAR tú. Cambia CUPO y re-pega para el siguiente.");
})();