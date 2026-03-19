# Domande Essenziali - Director Sapien
## Strategia: Integrazione a Costo Zero + Partnership

**Data:** 2026-03-19  
**Obiettivo:** Ridurre i costi di integrazione da $20K/mese a $0  
**Context:** Poli-News vuole verificare qualità quiz + reader comprehension via Sapien

---

## 🎯 BLOCCO 1: Token Economics & Cost Reduction

### Domanda 1: "Modello di incentivi per Adapter"
```
DOMANDA:
"Nel documento di architettura, vediamo che gli Adapters possono guadagnare fee.
Qual è il modello di fee per un Adapter tecnico come Poli-News?
Es. potremmo guadagnare il 1-2% del volume transazionale?"

PERCHÉ:
└─ Se Poli-News diventa Adapter ufficiale Sapien, potremmo guadagnare fee
└─ Ciò coprirebbe parte/totale dei costi di integrazione

ASPETTATE RISPOSTA COME:
├─ "Adapter fee: 2-5% di ogni transazione"
├─ "Al raggiungimento di X volume, diventate Adapter certified"
└─ "Volume richiesto: Y transazioni/mese"
```

### Domanda 2: "Grant & Hackathon Program"
```
DOMANDA:
"Sapien ha un programma di grant per i partner early-stage?
Es. matching funds per cover i costi di integrazione nei primi 3 mesi?"

PERCHÉ:
└─ Molti protocol hanno grant programs esattamente per questo
└─ Potremmo richiede $50-100K in SAPIEN token per coprire sviluppo

ASPETTATE:
├─ "Grant program: Sì/No"
├─ Se sì: "Amount range, termine richiesta, approval timeline"
├─ "Hackathon bounties disponibili? Es. '$10K per completare integrazione iframe'"
```



### Domanda 4: "Token Allocation per Partnership"
```
DOMANDA:
"Quale sarebbe l'allocazione di token SAPIEN per noi come partner
se raggiungessimo milestone specifici?
Es. X token per 10K transactions, Y token per 100 publishers integrati?"

PERCHÉ:
└─ Anziché pagare in USD, possiamo ricevere token come incentivo
└─ Se SAPIEN token sale, il valore degli incentivi cresce = win-win

ASPETTATE:
├─ "Milestone-based token allocation: Sì"
├─ "Es. 50K SAPIEN per raggiungere 10K transazioni"
├─ "Unlocking schedule: monthly/quarterly"
```

### Domanda 5: "Revenue Share Model - Alternative"
```
DOMANDA:
"Invece che pagare per ogni transaction, potremmo operare con
un revenue share model? Es. Poli-News prende 30% di tutti i SAPIEN
distribuiti attraverso i nostri quiz verification projects?"

PERCHÉ:
└─ Questo trasforma i costi in revenue (negative cost!)
└─ Allinea i nostri incentivi: vogliamo più transazioni

ASPETTATE:
├─ "Possibile revenue share model: Y%"
├─ "O: 'Standard è pay-per-transaction, ma possiamo negoziare per partner'"
└─ "Threshold: raggiunto Y volume/mese, potete agganciare revenue share"
```

---

## 🏗️ BLOCCO 2: Architettura & Integrazione Tecnica

### Domanda 6: "SDK / Library Support"
```
DOMANDA:
"Esiste un SDK ufficiale Sapien per Python/FastAPI?
Se no, qual è la curva di apprendimento per integrare direttamente
i contratti via web3.py o ethers.js?"

PERCHÉ:
└─ Vogliamo evitare di scrivere custom contract integrations
└─ Un SDK reduce development time & cost

ASPETTATE:
├─ "SDK disponibile: Sì (TypeScript/Python/Go)"
├─ "Se no: maintenete voi un wrapper open-source per Python?"
└─ "Estimated dev time senza SDK: 2-3 weeks"
```

### Domanda 7: "Testnet & Staging Environment"
```
DOMANDA:
"Possiamo sviluppare su Sapien testnet gratuitamente?
Dopo development, qual è il processo per andare to mainnet?
Esistono fees di deployment?"

PERCHÉ:
└─ Vogliamo testare gratis prima di spendere sulla mainnet
└─ Sappiamo quanti gas/contratto interaction cost

ASPETTATE:
├─ "Testnet: Sì, faucet disponibile con testnet SAPIEN"
├─ "Mainnet fee: Standard Ethereum gas (no Sapien premium)"
└─ "Deployment cost stimato: $500-2000 uno-tanto"
```

### Domanda 8: "Sapien Contract Upgrades & Breaking Changes"
```
DOMANDA:
"Qual è il versioning policy per Sapien contracts?
Se il protocol fa un upgrade, potrebbe rompere la nostra integrazione?
Come potreste notificarci in anticipo?"

PERCHÉ:
└─ Non vogliamo che un upgrade Sapien ci costi refactoring
└─ Vogliamo SLA su breaking changes

ASPETTATE:
├─ "Protocol versioning: Semantic versioning"
├─ "Breaking changes: preavviso minimo di 30 giorni"
└─ "Backward compatibility: X version maintained in parallel"
```

---

## 💰 BLOCCO 3: Business Model & Growth

### Domanda 9: "White-Label vs Branded"
```
DOMANDA:
"Potremmo offrire 'Verified Comprehension' come servizio branded:
'Poli-News Quality Badge' piuttosto che 'Powered by Sapien'?
Come Sapien gestisce la co-branding con i partner?"

PERCHÉ:
└─ Vogliamo che i nostri publisher di terze parti videro il brand Poli-News
└─ Non vogliamo che Sapien overshadow il nostro brand

ASPETTATE:
├─ "Sì, co-branding è standard per partner tier"
├─ "Guideline: Sapien logo + clear 'powered by' attribution"
└─ "Es. da loro: 'Verified by Poli-News (powered by Sapien Protocol)'"
```

### Domanda 10: "Multi-Chain Deployment"
```
DOMANDA:
"Sapien è deployato su chain multiple? Es. Ethereum, Polygon, Arbitrum?
Potremmo scegliere una chain con gas più basso (es. Polygon) per ridurre costi?"

PERCHÉ:
└─ Ethereum mainnet è caro (~$5-50 per transaction)
└─ Polygon gas è 1/100 di Ethereum
└─ Potrebbe ridurre drasticamente i costi

ASPETTATE:
├─ "Sapien deployments: Ethereum, Polygon, Arbitrum (Q2 2026)"
├─ "Gas cost su Polygon: ~$0.01-0.1 per transaction"
└─ "Se usiamo Polygon: costs $100-1000/mese instead of $20K"
```

### Domanda 11: "Batch Processing & Aggregation"
```
DOMANDA:
"Invece di creare un Sapien project per ogni quiz,
potremmo aggregare 100 quiz in un singolo batch project
per ridurre onchain transactions?
Sapien supporta questo?"

PERCHÉ:
└─ Meno transazioni = meno gas = costi ridotti
└─ Es. 1 transaction per 100 quiz = 100× riduzione costi

ASPETTATE:
├─ "Batch processing: non standard, ma possibile via custom contract"
├─ "Alternate: 'Aggregation contracts' che Sapien fornisce"
└─ "Cost reduction: potenziale 50-90% se batched"
```

---

## 🤝 BLOCCO 4: Partnership & Ecosystem

### Domanda 12: "Official Partnership Tier"
```
DOMANDA:
"Quali sono i criteri per diventare 'Official Sapien Partner'?
Quali benefit vengono con questo? Es. featured listing, dev support, etc?"

PERCHÉ:
└─ Official partner status = credibilità + visibility
└─ Potrebbero offrire dev resources gratis per partner ufficiali

ASPETTATE:
├─ "Partner criteria: integration + X transaction volume"
├─ "Benefits: technical support, co-marketing, badge, prioritized support"
└─ "Qual è il threshold? Es. '10K transaction/mese = official partner'"
```

### Domanda 13: "Validator Network Incentives"
```
DOMANDA:
"Nel nostro modello, abbiamo bisogno di validator per verificare quiz.
Potremmo accedere a un network di validator già-incentivizzato nel Sapien ecosystem?
O dobbiamo reclutarli noi?"

PERCHÉ:
└─ Non vogliamo dovere pagare validator bonus on-top
└─ Se Sapien ha già validator pool, potremmo usarli

ASPETTATE:
├─ "Validator pool: Sì, pubblicamente disponibile"
├─ "Loro ricevono rewards direttamente dal Sapien protocol, non da noi"
└─ "Cost to Poli-News: $0 per validator recruiting"
```

### Domanda 14: "DAO Governance & Voting"
```
DOMANDA:
"Come partner/Adapter strategico, potremmo avere una voce nel governance di Sapien?
Es. proporre nuovi verifiche types, votare su protocol parameters?"

PERCHÉ:
└─ Se Sapien è decentralizzato, vogliamo input su decisioni che ci impattano
└─ Ciò ci allinea meglio con il protocol

ASPETTATE:
├─ "DAO governance: snapshot voting on Sapien governance token"
├─ "Partner voting weight: Y (es. 5x multiplier su stake)"
└─ "Upcoming votes: quando e dove partecipare?"
```

---

## 📊 BLOCCO 5: Financial & Legal

### Domanda 15: "Token Price & Volatility Hedging"
```
DOMANDA:
"Se riceviamo rewards in SAPIEN token (per coprire i costi),
come possiamo hedge contro la volatilità?
Sapien offre acquisto di token a prezzo fisso per partner,
o futures contracts?"

PERCHÉ:
└─ Se SAPIEN token crolla, il valore dei nostri reward diminuisce
└─ Vogliamo price stability per i nostri budget

ASPETTATE:
├─ "Token hedging: Sapien partner hedge fund (Y%)"
├─ "Alternate: partner swaps a prezzo fisso (es. $0.10 price floor)"
└─ "Scadenza: per quanto tempo garantito il prezzo fisso?"
```

### Domanda 16: "MSA & Legal Framework"
```
DOMANDA:
"Qual è il processo per firmmare un Master Service Agreement con Sapien?
Ci sono template? Quali clausole sono non-negotiable?"

PERCHÉ:
└─ Vogliamo juridical clarity prima di investire
└─ Non vogliamo sorprese legali

ASPETTATE:
├─ "MSA template: disponibile (email: partnerships@sapien.io)"
├─ "Non-negotiable: X, Y, Z"
└─ "Timeline: 2 settimane legal review"
```

---

## 💡 BLOCCO 6: Cost-Zero Specific Questions

### Domanda 17: "Revenue Sharing Calculation Example"
```
DOMANDA:
"Mi darebbe un esempio numerico di revenue sharing?
Scenario: Poli-News processa 10,000 quiz/mese,
ogni quiz allocation ha 100 SAPIEN reward pool.
Sapien riceve cosa, noi riceviamo cosa?"

PERCHÉ:
└─ Vogliamo numeri concreti per capire se è conveniente

ASPETTATE RISPOSTA:
├─ "10K quiz × 100 SAPIEN = 1M SAPIEN total allocation"
├─ "Sapien protocol fee: 2% ($20K) → Sapien DAO"
├─ "Remaining 980K SAPIEN:
│   ├─ Contributors: 450K (45%)
│   ├─ Validators: 100K (10%)  
│   └─ Adapter fee (Poli-News): 430K (43%)"
├─ "Poli-News earnings: 430K SAPIEN/mese (~$43K USD a $0.10/token)"
└─ "Net: +$23K revenue (NEGATIVE COST = Profit!)"
```

### Domanda 18: "Token Lockup & Liquidity"
```
DOMANDA:
"Se riceviamo token SAPIEN come fee/reward,
possiamo venderli subito per USD, o sono lockati?
Qual è la liquidity timeline?"

PERCHÉ:
└─ Vogliamo convertire SAPIEN to USD per coprire i costi operativi
└─ Se token sono locked 6 mesi, non possiamo usarli

ASPETTATE:
├─ "Lockup period: No lockup per Adapter fee"
├─ "Liquidity: SAPIEN listed on Uniswap/Binance"
├─ "Spreads: Y% (es. 0.5-2% slippage)"
└─ "Daily volume: Z (verificate liquidità senza crollarla)"
```

### Domanda 19: "Risk: Se Sapien Protocol Fallisce?"
```
DOMANDA:
"Scenario pessimista: Se Sapien protocol fallisce o è hacked,
come siamo protetti? C'è un protocol insurance fund?"

PERCHÉ:
└─ Risk management: non vogliamo che un fallimento Sapien danneggi Poli-News
└─ Vogliamo sapere exit strategy

ASPETTATE:
├─ "Protocol insurance: Y (Nexus Mutual coverage available)"
├─ "Smart contract audit status: Z auditor, findings resolved"
├─ "Emergency pause function: Sì/No"
└─ "Historical incident examples: Y (se esistono)"
```

---

## 🎬 BLOCCO 7: Timeline & Execution

### Domanda 20: "Roadmap & Feature Parity"
```
DOMANDA:
"Qual è la Sapien product roadmap per i prossimi 6-12 mesi?
Sono previste features che potrebbero migliorare il nostro use case?
Es. native fee sharing, batch processing, etc?"

PERCHÉ:
└─ Se nuove features arrivano tra 2 mesi, aspettiamo
└─ Se non sono pianificate, facciamo custom implementation

ASPETTATE:
├─ "Q2 2026: Batch processing contracts"
├─ "Q3 2026: DAO governance token launch"
├─ "Q4 2026: Multi-chain expansion"
└─ "Best timing per Poli-News integration: Q2-Q3 (after batch contracts)"
```

### Domanda 21: "Dedicated Developer Support"
```
DOMANDA:
"Come parte della partnership, avremo un dedicated Sapien dev
assegnato al nostro progetto? Per quanto tempo?"

PERCHÉ:
└─ Support dedicato reduce development time
└─ Potrebbe essere worth tutto il value di una partnership

ASPETTATE:
├─ "Dedicated dev support: per partner tier Y"
├─ "Duration: 3-6 months (during integration phase)"
└─ "Cost: included in partnership, o paid separately?"
```

---

## 📋 BONUS: Questions per Negoziare a Zero Cost

### Strategy: "Cost Absorption via Fee Share"
```
PROPOSTA DA FARE:
"Sapien, vorremmo proporre una partnership dove:
├─ I costi di integrazione Poli-News = $20K/mese
├─ Vengono completamente finanziati da una fee share sul volume generato
├─ Non pagare niente fino a reach breakeven volume

MECCANICA:
├─ Poli-News integra Sapien (development cost: $50K one-time)
├─ Per i primi 3 mesi: Poli-News paga 0 SAPIEN
├─ Poli-News genera volume: 10K quiz × 100 SAPIEN = 1M SAPIEN/mese
├─ Sapien prende 2% protocol fee: 20K SAPIEN
├─ Poli-News prende X% adapter fee (negoziato, es. 30-40%)
├─ 30% di 1M = 300K SAPIEN/mese (~$30K)
├─ Breakeven: 1 mese! Dopo è pure profit per Poli-News

DOMANDA:
'Potremmo operare sotto questo modello per i primi 3-6 mesi,
finché il volume non copre i costi di integrazione?'"
```

### Strategy: "Equity/Token Stake"
```
PROPOSTA 2:
"Se Sapien è un token-gated DAO, potremmo ricevere
un programmatic allocation di token come partner?
Es. 0.5% di max supply = equity stake nel protocol"

BENEFIT:
├─ Se Sapien token cresce 10-100×, il nostro stake diventa worth 100K+
├─ Allinea i nostri incentivi: vogliamo Sapien di successo
├─ Cost to Sapien: token allocation (no cash cost)
├─ Cost to Poli-News: 0 (anzi, guadagniamo)
```

---

## 🎯 Domande di Follow-up (post-risposta)

Una volta ricevute risposte al director, chedi:

1. **"Potremmo fare una call di planning?** Vorremmo condividire il documento di integrazione con il vostro team tecnico e allineare su timeline."

2. **"Chi è il vostro partnership lead?** Possiamo escalare queste domande a chi ha authority nelle decisioni di fee sharing?"

3. **"Avete altri partner con modelli simili?** Ci piacerebbe parlare con 1-2 partner di fase simile per best practices."

4. **"Quando possiamo fare una proposal formale?"** Vogliamo documentare questa partnership in una FPA (Framework Partnership Agreement).

---

## 🚀 Summary: Strategy Roadmap

| Elemento | Strategia | Costo Presunto |
|----------|-----------|-----------------|
| **Token Economics** | Revenue share instead of paying | -$20K/mese |
| **Adapter Fee** | 30-40% di transaction volume | +$20-30K/mese profit |
| **Grant Program** | Apply per development funding | +$50-100K one-time |
| **Multi-chain** | Deploy on Polygon (cheap gas) | -$19K/mese (vs Ethereum) |
| **Batch Processing** | Aggregare 100 quiz per transaction | -80-90% gas costs |
| **Partnership Token Share** | Receive SAPIEN allocations | +$100K-500K (se appreciation) |
| **Total Potential** | Combined all above | **$0 cost + profit!** |

---

**Status:**  Pronto per call con director Sapien  
**Prossimo Step:** Schedule 30-min call, prep questo documento come agenda  
**Owner:** [Voi]  
**Date:** 2026-03-19
