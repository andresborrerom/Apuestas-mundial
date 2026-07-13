#!/usr/bin/env python3
"""SEMIS CSC — optim de los 5 cupos con el field REAL (PDF 11.7).
Mide el tradeoff E[premio total] (copar plata) vs P(recuperar #1) (casilla 50%).
Solo 2 partidos (Fra-Esp, Ing-Arg). EV-máx de ambos = 1-1 (empate)."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import analizar_partido, odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC.experimento_r32 import ajuste_120, ranking_fills

AQUI = os.path.dirname(os.path.abspath(__file__)); PARAMS = RONDAS["semis"]; G=7; PRECIO=100_000; S=40000
FD="/tmp/claude-0/-home-user-Apuestas-mundial/d76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/field11.json"

def matrices(snap):
    ev=json.load(open(snap,encoding="utf-8")); M90,lam=[],[]
    for e in ev:
        c=odds_api.consenso_evento(e,linea_pref=2.5)
        if not c["cuotas_1x2"]: continue
        r=analizar_partido(cuotas_1x2=c["cuotas_1x2"],regla=regla_de_ronda("semis"),
            cuotas_ou=c["cuotas_ou"],linea_ou=c["linea"] or 2.5,sesgo_goles=0.0,max_goles_relleno=7)
        M90.append(r["matriz"]); lam.append((r["modelo"]["lambda_local"],r["modelo"]["lambda_visita"]))
    M120=[ajuste_120(M,lL,lV,0.45) for M,(lL,lV) in zip(M90,lam)]
    return [marcadores.aplicar_sesgo_goles(M,0.05) for M in M120]

def perfiles_de(Ms):
    rk=ranking_fills(Ms); Mn=len(Ms)
    def ra(k): return (np.array([rk[i][k][0] for i in range(Mn)]), np.array([rk[i][k][1] for i in range(Mn)]))
    P={"D(EV-máx)":ra(0),"A(rank2)":ra(1),"B(rank3)":ra(2)}
    dh,da=ra(0); r2h,r2a=ra(1)
    for i in range(Mn):
        h=dh.copy();a=da.copy();h[i]=r2h[i];a[i]=r2a[i]; P[f"s{i+1}(2º P{i+1})"]=(h,a)
    return P

def main():
    Ms=matrices(os.path.join(AQUI,"semi_odds_snapshot.json"))
    fd=json.load(open(FD)); rivals=np.array([p for _,p in fd["rivals"]],float); Ef=len(rivals)
    o=sorted(fd["ours"].items(),key=lambda kv:-kv[1])
    labels=[k.replace("ANDRES BORRERO ","B") for k,_ in o]; ours_pts=np.array([v for _,v in o],float)
    perf=perfiles_de(Ms); pn=list(perf)
    print(f"Cupos: {list(zip(labels,ours_pts.astype(int)))}")
    print(f"Líder field: {fd['rivals'][0]}  ·  Perfiles: {pn}\n")
    rng=np.random.default_rng(1)
    gh,ga=sp.muestrear_torneos(Ms,S,rng,G)
    fh,fa=sp.generar_field_mix(Ms,Ef,{"opt":.15,"cal":.35,"hum":.50},PARAMS,rng,G)
    field_tot=rivals[:,None]+sp._puntos(fh,fa,gh,ga,PARAMS)          # (Ef,S)
    field_max=field_tot.max(axis=0)                                  # mejor rival por sim
    premio=sp.PREMIOS*(Ef+5)*PRECIO
    jit=rng.random((5,S))*1e-6
    pg={nm:sp._puntos(np.array([ph]),np.array([pa]),gh,ga,PARAMS)[0] for nm,(ph,pa) in perf.items()}
    def evaluar(assign):
        our=ours_pts[:,None]+np.array([pg[a] for a in assign])+jit
        fabove=(field_tot[None,:,:]>our[:,None,:]).sum(axis=1)
        oabove=(our[:,None,:]>our[None,:,:]).sum(axis=0)
        rank=fabove+oabove
        pr=np.where(rank<5,premio[np.clip(rank,0,4)],0.0)
        inm=rank<5
        p1=(our.max(axis=0)>field_max).mean()      # P(algún cupo nuestro es #1 global)
        return pr.sum(0).mean(), inm.mean(axis=1), inm.sum(0).mean(), p1
    base=["D(EV-máx)"]*5
    bp,binm,bslots,bp1=evaluar(base)
    print(f"BASELINE 5×EV-máx(1-1):  E[premio]={bp:,.0f}  E[slots]={bslots:.2f}  P(#1 nuestro)={bp1*100:.1f}%")
    print("  P(cupo en plata):", {l:f'{p*100:.0f}%' for l,p in zip(labels,binm)})
    # SWEEP: cambiar un cupo
    print("\nSWEEP — cambiar SOLO un cupo (resto EV-máx):  Δpremio | P(#1)")
    for i,l in enumerate(labels):
        best=None
        for p in pn:
            a=list(base);a[i]=p; pr,_,_,p1=evaluar(a)
            if best is None or pr>best[1]: best=(p,pr,p1)
        # también el que maximiza P(#1)
        bestp1=max(pn,key=lambda p:evaluar([p if j==i else "D(EV-máx)" for j in range(5)])[3])
        _,_,_,p1v=evaluar([bestp1 if j==i else "D(EV-máx)" for j in range(5)])
        print(f"  {l}({int(ours_pts[i])}): max-premio->{best[0]:12} (Δ{best[1]-bp:+,.0f}, P#1={best[2]*100:.0f}%)  |  max-P#1->{bestp1:12} (P#1={p1v*100:.0f}%)")
    # GREEDY para E[premio]
    assign=list(base);cur,_,_,_=evaluar(assign);imp=True
    while imp:
        imp=False
        for i in range(5):
            for p in pn:
                a=list(assign);a[i]=p;pr,_,_,_=evaluar(a)
                if pr>cur+1: assign=a;cur=pr;imp=True
    _,inm,slots,p1=evaluar(assign)
    print(f"\nÓPTIMO E[premio]={cur:,.0f} (+{cur-bp:,.0f}) E[slots]={slots:.2f} P(#1)={p1*100:.1f}%")
    for i,l in enumerate(labels): print(f"   {l}({int(ours_pts[i])}): {assign[i]:12} P(plata)={inm[i]*100:.0f}%")

if __name__=="__main__": main()

def escenarios():
    Ms=matrices(os.path.join(AQUI,"semi_odds_snapshot.json"))
    fd=json.load(open(FD)); rivals=np.array([p for _,p in fd["rivals"]],float); Ef=len(rivals)
    o=sorted(fd["ours"].items(),key=lambda kv:-kv[1])
    ours_pts=np.array([v for _,v in o],float)
    perf=perfiles_de(Ms)
    rng=np.random.default_rng(1)
    gh,ga=sp.muestrear_torneos(Ms,S,rng,G)
    fh,fa=sp.generar_field_mix(Ms,Ef,{"opt":.15,"cal":.35,"hum":.50},PARAMS,rng,G)
    field_tot=rivals[:,None]+sp._puntos(fh,fa,gh,ga,PARAMS); field_max=field_tot.max(0)
    premio=sp.PREMIOS*(Ef+5)*PRECIO; jit=rng.random((5,S))*1e-6
    pg={nm:sp._puntos(np.array([ph]),np.array([pa]),gh,ga,PARAMS)[0] for nm,(ph,pa) in perf.items()}
    def ev(assign):
        our=ours_pts[:,None]+np.array([pg[a] for a in assign])+jit
        fabove=(field_tot[None,:,:]>our[:,None,:]).sum(1); oabove=(our[:,None,:]>our[None,:,:]).sum(0)
        rank=fabove+oabove; pr=np.where(rank<5,premio[np.clip(rank,0,4)],0.0)
        return pr.sum(0).mean(),(rank<5).mean(1),(rank<5).sum(0).mean(),(our.max(0)>field_max).mean()
    D="D(EV-máx)";B="B(rank3)";A="A(rank2)"
    configs={
      "1 recuperar #1 (B4,B2=1-2)":[B,D,B,D,D],
      "2 blindar (todo EV-máx)":[D,D,D,D,D],
      "3a agresivo (B4,B1,B2=1-2)":[B,B,B,D,D],
      "3b agresivo mixto (B4=1-2,B1=2-1,B2=1-2,B5=2-1)":[B,A,B,A,D],
    }
    labels=[k.replace("ANDRES BORRERO ","B") for k,_ in o]
    print(f"{'config':46}{'E[premio]':>12}{'P(#1)':>8}{'slots':>7}")
    for nm,a in configs.items():
        pr,inm,sl,p1=ev(a)
        print(f"{nm:46}{pr:>12,.0f}{p1*100:>7.0f}%{sl:>7.2f}")
