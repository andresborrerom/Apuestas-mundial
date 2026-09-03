(function(){
  var ins=document.querySelectorAll('input');
  console.log('inputs totales:',ins.length);
  console.log('si es 0 -> el form está en un IFRAME; cambia el contexto de la consola al frame googleusercontent.');
  var ej=[].slice.call(ins).slice(0,4).map(function(i){return {type:i.type,name:i.name,id:i.id,ph:i.placeholder};});
  console.log('primeros inputs:',ej);
  // muestra el texto del contenedor del primer input (para ver cómo nombran los equipos)
  if(ins[0]){var n=ins[0];for(var u=0;u<7&&n;u++){n=n.parentElement;if(n&&n.querySelectorAll('input').length>=2){console.log('texto contenedor de 1er partido:',JSON.stringify(n.textContent.trim().slice(0,120)));break;}}}
})();