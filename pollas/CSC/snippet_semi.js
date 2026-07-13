(function(){
  /* CSC SEMIS G3 (auditada, field 11.7v2). Llena EMAIL + NOMBRE DE CUPO + marcadores. NO envía. */
  var CUPO = 1;  // <<<<<< cambia 1..5 y re-pega. B1:2-1/1-2 · B2:2-1/2-1 · B3:2-2/1-2 · B4:1-2/2-1 · B5:1-2/1-2
  var EMAIL = "andres.borrerom@gmail.com";
  var NOMBRE = "ANDRES BORRERO " + CUPO;
  var PART = [{"L": "Francia", "V": "España", "aL": ["francia", "france"], "aV": ["espana", "spain"], "s": [[2, 1], [2, 1], [2, 2], [1, 2], [1, 2]]}, {"L": "Inglaterra", "V": "Argentina", "aL": ["inglaterra", "england"], "aV": ["argentina"], "s": [[1, 2], [2, 1], [1, 2], [2, 1], [1, 2]]}];
  function k(s){return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z]/g,"");}
  function hasA(t,al){for(var i=0;i<al.length;i++){if(t.indexOf(al[i])>=0)return true;}return false;}
  function setVal(el,v){el.value=v;["input","change","blur","keyup"].forEach(function(ev){el.dispatchEvent(new Event(ev,{bubbles:true}));});}
  var used=[];
  var allIn=[].slice.call(document.querySelectorAll("input,textarea")).filter(function(i){return i.type!=="hidden";});
  var inputs=allIn.filter(function(i){return i.type!=="email";});
  if(inputs.length<PART.length*2){console.log("%c⚠️ CONTEXTO EQUIVOCADO: en el dropdown arriba-izq de la consola elige userHtmlFrame (userCodeAppPanel) y re-pega.","font-size:16px;font-weight:bold;color:red");return;}
  var els=[].slice.call(document.querySelectorAll("h1,h2,h3,h4,h5,h6,div,span,p,label,td,li,b,strong"));
  function anchorInput(keywords){
    var lab=null,len=1e9;
    for(var i=0;i<els.length;i++){var t=k(els[i].textContent||"");if(!t)continue;
      for(var j=0;j<keywords.length;j++){if(t.indexOf(keywords[j])>=0){var L=(els[i].textContent||"").length;if(L<len){len=L;lab=els[i];}break;}}}
    if(!lab)return null;
    var inside=allIn.filter(function(x){return lab.contains(x)&&used.indexOf(x)<0;});
    if(inside.length)return inside[0];
    var foll=allIn.filter(function(x){return (lab.compareDocumentPosition(x)&Node.DOCUMENT_POSITION_FOLLOWING)&&used.indexOf(x)<0;});
    return foll.length?foll[0]:null;
  }
  /* 1) EMAIL */
  var emEl=allIn.filter(function(i){return i.type==="email";})[0]||anchorInput(["correoelectronico","correo","email"]);
  if(emEl){setVal(emEl,EMAIL);used.push(emEl);}
  /* 2) NOMBRE/CUPO */
  var nomEl=anchorInput(["nombreyapellido","nombrecompleto","nombre","participante"]);
  if(nomEl){setVal(nomEl,NOMBRE);used.push(nomEl);}
  /* 3) MARCADORES */
  var ok=0,miss=[],log=[];
  PART.forEach(function(p){
    var lab=null,len=1e9;
    for(var i=0;i<els.length;i++){var t=k(els[i].textContent||"");
      if(hasA(t,p.aL)&&hasA(t,p.aV)){var L=(els[i].textContent||"").length;if(L<len){len=L;lab=els[i];}}}
    if(!lab){miss.push(p.L+" vs "+p.V);return;}
    var cand2=inputs.filter(function(x){return lab.contains(x)&&used.indexOf(x)<0;});
    if(cand2.length!==2){cand2=inputs.filter(function(x){return (lab.compareDocumentPosition(x)&Node.DOCUMENT_POSITION_FOLLOWING)&&used.indexOf(x)<0;});}
    if(cand2.length<2){miss.push(p.L+" vs "+p.V);return;}
    var gl=p.s[CUPO-1][0],gv=p.s[CUPO-1][1];
    setVal(cand2[0],gl);setVal(cand2[1],gv);used.push(cand2[0],cand2[1]);ok++;
    log.push("   "+p.L+" "+gl+"-"+gv+" "+p.V);
  });
  /* 4) RESUMEN GRANDE para verificación visual */
  var idok=(emEl?"✉️ "+EMAIL:"✉️ ⚠️ EMAIL NO ENCONTRADO (llénalo a mano)")+"  ·  "+(nomEl?"👤 "+NOMBRE:"👤 ⚠️ NOMBRE NO ENCONTRADO (llénalo a mano)");
  console.log("%c══ VAS A ENVIAR EL CUPO "+CUPO+" ══","font-size:20px;font-weight:bold;color:white;background:"+(ok==PART.length&&emEl&&nomEl?"green":"darkorange")+";padding:4px 10px");
  console.log("%c"+idok,"font-size:14px;font-weight:bold");
  console.log("%cMarcadores llenados "+ok+"/"+PART.length+":\n"+log.join("\n"),"font-size:13px");
  if(miss.length)console.warn("FALTAN (a mano):",miss);
  console.log("%cVERIFICA en pantalla que el nombre diga '"+NOMBRE+"' antes de dar Enviar.","font-size:13px;color:orange;font-weight:bold");
})();