const {questions}=JSON.parse(document.getElementById("data").textContent);
const area=document.getElementById("play");
let i=0,score=0;
function add(tag,text,host=area){
  const element=document.createElement(tag);
  if(text!==null)element.textContent=text;
  host.append(element);
  return element;
}
function button(label,action,host=area){
  const element=add("button",label,host);
  element.type="button";
  element.onclick=action;
  return element;
}
function render(){
  area.replaceChildren();
  if(i===questions.length){
    add("h2","Quiz completato");
    add("p",score+" / "+questions.length+" risposte corrette");
    button("Ricomincia",()=>{i=0;score=0;render();}).focus();
    return;
  }
  const q=questions[i];
  add("p",(i+1)+"/"+questions.length);
  add("p",q.t).className="question";
  const options=add("div",null);options.className="quiz-options";
  const controls=q.o.map((word,j)=>button(word,()=>answer(j),options));
  const feedback=add("p","");feedback.className="feedback";feedback.setAttribute("role","status");
  function answer(j){
    const correct=j===q.answer;
    if(correct)score++;
    controls.forEach((control,k)=>{
      control.disabled=true;
      if(k===q.answer)control.classList.add("good");
      else if(k===j)control.classList.add("bad");
    });
    feedback.textContent=correct?"Risposta corretta.":"Risposta corretta: "+q.o[q.answer]+".";
    if(q.explanation) feedback.textContent+=" "+q.explanation;
    button("Avanti",()=>{i++;render();area.querySelector("button")?.focus();}).focus();
  }
}
render();
