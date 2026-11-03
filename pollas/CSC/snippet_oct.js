(function(){
  /* CSC MIXTO+120'. CUPO = nº de ANDRES BORRERO (1..5). Cambia y re-pega. NO envía. */
  var CUPO = 4;  // <<<<<< 4=ancla(B4) · 1,2=defensivas · 3,5=lotería
  var PART = [{"L": "Canadá", "V": "Marruecos", "aL": ["canada"], "aV": ["marruecos", "morocco"], "s": [[1, 2], [1, 2], [1, 3], [1, 2], [0, 2]]}, {"L": "Paraguay", "V": "Francia", "aL": ["paraguay"], "aV": ["francia", "france"], "s": [[1, 3], [1, 3], [1, 3], [1, 2], [0, 2]]}, {"L": "Brasil", "V": "Norway", "aL": ["brasil", "brazil"], "aV": ["noruega", "norway"], "s": [[2, 1], [2, 1], [3, 1], [2, 1], [1, 1]]}, {"L": "México", "V": "Inglaterra", "aL": ["mexico"], "aV": ["inglaterra", "england"], "s": [[1, 1], [1, 1], [1, 1], [1, 2], [2, 1]]}, {"L": "Portugal", "V": "España", "aL": ["portugal"], "aV": ["espana", "spain"], "s": [[1, 2], [1, 2], [1, 3], [1, 2], [1, 1]]}, {"L": "USA", "V": "Bélgica", "aL": ["usa", "estadosunidos", "unitedstates", "eeuu"], "aV": ["belgica", "belgium"], "s": [[1, 2], [2, 1], [2, 1], [1, 2], [1, 1]]}, {"L": "Argentina", "V": "Egipto", "aL": ["argentina"], "aV": ["egipto", "egypt"], "s": [[2, 1], [2, 1], [2, 0], [2, 1], [3, 1]]}, {"L": "Suiza", "V": "Colombia", "aL": ["suiza", "switzerland"], "aV": ["colombia"], "s": [[1, 2], [1, 2], [1, 1], [1, 2], [2, 1]]}];
  function k(s){return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z]/g,"");}
  function hasA(t,al){for(var i=0;i<al.length;i++){if(t.indexOf(al[i])>=0)return true;}return false;}
  function setVal(el,v){el.value=v;["input","change","blur","keyup"].forEach(function(ev){el.dispatchEvent(new Event(ev,{bubbles:true}));});}
  var inputs=[].slice.call(document.querySelectorAll("input")).filter(function(i){return i.type!=="email"&&i.type!=="hidden";});
  if(inputs.length<PART.length){console.log("%c⚠️ CONTEXTO EQUIVOCADO: en el dropdown arriba-izq de la consola elige userHtmlFrame (userCodeAppPanel) y re-pega.","font-size:16px;font-weight:bold;color:red");return;}
  var els=[].slice.call(document.querySelectorAll("h1,h2,h3,h4,h5,h6,div,span,p,label,td,li,b,strong"));
  var used=[],ok=0,miss=[],log=[];
  PART.forEach(function(p){
    var lab=null,len=1e9;
    for(var i=0;i<els.length;i++){var t=k(els[i].textContent||"");
      if(hasA(t,p.aL)&&hasA(t,p.aV)){var L=(els[i].textContent||"").length;if(L<len){len=L;lab=els[i];}}}
    if(!lab){miss.push(p.L+" vs "+p.V);return;}
    var inside=inputs.filter(function(x){return lab.contains(x)&&used.indexOf(x)<0;});
    var foll=inputs.filter(function(x){return (lab.compareDocumentPosition(x)&Node.DOCUMENT_POSITION_FOLLOWING)&&used.indexOf(x)<0;});
    var cand=(inside.length===2)?inside:foll;
    if(cand.length<2){miss.push(p.L+" vs "+p.V);return;}
    var gl=p.s[CUPO-1][0],gv=p.s[CUPO-1][1];
    setVal(cand[0],gl);setVal(cand[1],gv);used.push(cand[0],cand[1]);ok++;
    log.push(p.L+" "+gl+"-"+gv+" "+p.V);
  });
  console.log("%cCSC BORRERO "+CUPO+": llené "+ok+"/"+PART.length,"font-size:15px;font-weight:bold;color:"+(ok==PART.length?"green":"orange"));
  console.log(log.join("\n"));
  if(miss.length)console.warn("FALTAN (a mano):",miss);
})();