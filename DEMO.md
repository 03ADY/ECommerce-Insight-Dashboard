# CommerceIQ — Presenter Guide (2 min)

```powershell
.\scripts\start-demo.ps1
```

**http://127.0.0.1:8503** · Preview mockup: `docs/demo-preview.svg`

## Recommended flow

1. Leave **Present mode** ON and select **Last 90 days** scenario  
2. Call out KPI deltas and the **revenue goal** progress bar  
3. Read the **Executive insights** cards (auto-generated)  
4. Expand **Executive brief** → offer to download `.md` for stakeholders  
5. **Overview** — trends; mention anomalies if flagged  
6. **Customers** — new vs returning + Pareto  
7. **RFM** — export **At Risk** CSV (marketing handoff moment)  
8. **Forecast** — cite **MAPE** as model quality check  
9. **Business ROI** — adjust uplift % in sidebar (turn Present mode off briefly)  
10. **Drill-down** — pick top category, show raw transactions  

## Scenarios to try live

| Scenario | Story |
|----------|--------|
| Last 90 days | Default — momentum narrative |
| Electronics focus | Merchandising deep-dive |
| Beauty & Clothing | Category bundle performance |
| Custom range | Audience asks “what about Q1?” |

## Pro tips

- Toggle **Present mode** off only when you need forecast/ROI sliders  
- **Revenue goal** = 0 auto-sets target to 110% of prior period  
- Duplicate download buttons: filtered CSV (sidebar) + executive brief + segment lists
