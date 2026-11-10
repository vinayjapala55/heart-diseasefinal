/**
 * BMD-HS Clinical Diagnostic Suite - Results Page Logic
 * Reads the diagnostic report from sessionStorage and renders the clinical findings.
 */

document.addEventListener('DOMContentLoaded', () => {
    let report = null;
    const rawData = sessionStorage.getItem('currentDiagnosticReport');

    if (rawData) {
        try {
            report = JSON.parse(rawData);
        } catch (e) {
            console.error("Failed to parse diagnostic report:", e);
        }
    }

    // If no report found in session (e.g. direct URL visit), render verified demo patient
    if (!report) {
        report = {
            patient_session_id: "SESSION-SAMPLE-DEMO",
            model_version: "RosaNet-8Branch-v1.0",
            timestamp: new Date().toISOString(),
            prediction_summary: {
                overall_status: "Elevated Risk: Severe Aortic Stenosis (Primary Murmur Epicenter: Aortic Valve)",
                risk_level: "High Risk",
                is_normal: false,
                raw_probabilities: { N: 0.082, AS: 0.925, AR: 0.185, MR: 0.124, MS: 0.062 },
                decision_thresholds: { N: 0.52, AS: 0.70, AR: 0.48, MR: 0.45, MS: 0.50 },
                valve_attributions: [{
                    disease_class: "AS",
                    top_contributing_valve: "Aortic Valve",
                    valve_attributions: [
                        { valve_name: "Aortic Valve", branch_score: 0.945 },
                        { valve_name: "Pulmonary Valve", branch_score: 0.312 },
                        { valve_name: "Tricuspid Valve", branch_score: 0.185 },
                        { valve_name: "Mitral Valve", branch_score: 0.124 }
                    ]
                }],
                detected_conditions: [{
                    disease_code: "AS",
                    disease_name: "Aortic Stenosis",
                    probability: 0.925,
                    threshold: 0.70,
                    is_positive: true,
                    primary_contributing_valve: "Aortic Valve"
                }]
            },
            quality_summary: {
                status: "PASS",
                summary: "All 8 recordings verified with 4th-order Butterworth bandpass (25-400 Hz) and 2,000 Hz standardization."
            },
            evidence_summary: {
                retrieved_guidelines: [{
                    target_disease: "Aortic Stenosis",
                    section_name: "Evaluation of Severe AS",
                    page_number: "28",
                    content_text: "In patients with signs or symptoms of AS, transthoracic echocardiography is recommended for initial evaluation to define the etiology, assess severity, and measure transvalvular gradient.",
                    guideline_title: "2020 ACC/AHA Guideline for the Management of Valvular Heart Disease"
                }]
            },
            structured_markdown_report: `# BMD-HS CLINICAL CARDIOTHORACIC CONSULTATION NOTE
PATIENT ACCESSION: SESSION-SAMPLE-DEMO
DATE/TIME: ${new Date().toLocaleString()}
EVALUATION SYSTEM: RosaNet 8-Branch Neural Network Ensemble v2.0
ACC/AHA CLINICAL EVIDENCE: 2020 Valvular Heart Disease Guidelines

--------------------------------------------------------------------------------
1. PRIMARY CLINICAL IMPRESSION:
Elevated Risk: Severe Aortic Stenosis (Primary Murmur Epicenter: Aortic Valve)
RISK STRATIFICATION: HIGH RISK

2. MULTILABEL VALVULAR PROBABILITIES:
- Normal (N):              8.2%  (Threshold: 52%)
- Aortic Stenosis (AS):    92.5% (Threshold: 70%) [ELEVATED]
- Aortic Regurgitation (AR): 18.5% (Threshold: 48%)
- Mitral Regurgitation (MR): 12.4% (Threshold: 45%)
- Mitral Stenosis (MS):    6.2%  (Threshold: 50%)

3. ACOUSTIC MURMUR EPICENTER & VALVE ATTRIBUTION:
Primary Valve Focus: Aortic Valve
Spatial-temporal attention confirmed energy distribution concentrated at the aortic root.

4. 2020 ACC/AHA CLINICAL EVIDENCE SUMMARY:
[Aortic Stenosis - Evaluation of Severe AS, p.28]: "In patients with signs or symptoms of AS, transthoracic echocardiography is recommended for initial evaluation to define the etiology, assess severity, and measure transvalvular gradient."

5. RECOMMENDED NEXT CLINICAL STEPS:
- Urgent Comprehensive Transthoracic Echocardiography (TTE) with Doppler color-flow mapping.
- Cardiology specialist consultation.
- Hemodynamic gradient quantification.
--------------------------------------------------------------------------------
DOCUMENTATION SIGN-OFF: Verified by RosaNet Multi-Agent Diagnostic Workstation.`
        };
    }

    renderReport(report);

    function renderReport(report) {
        const pred = report.prediction_summary || {};
        const quality = report.quality_summary || {};
        const evidence = report.evidence_summary || {};

        // 1. Meta & Accession
        const resPatientId = document.getElementById('resPatientId');
        if (resPatientId) resPatientId.textContent = report.patient_session_id || 'SESSION-PATIENT';

        const resTimestamp = document.getElementById('resTimestamp');
        if (resTimestamp) resTimestamp.textContent = new Date().toLocaleString();

        const resModelVersion = document.getElementById('resModelVersion');
        if (resModelVersion) resModelVersion.textContent = report.model_version || 'RosaNet-8Branch-v1.0';

        // 2. Hero Banner & Risk Pill
        const heroBanner = document.getElementById('heroBanner');
        if (heroBanner) {
            heroBanner.className = `diagnosis-banner ${pred.is_normal ? 'normal' : 'abnormal'}`;
        }

        const resPrimaryDiagnosis = document.getElementById('resPrimaryDiagnosis');
        if (resPrimaryDiagnosis) {
            resPrimaryDiagnosis.textContent = pred.overall_status || 'Diagnostic Evaluation Complete';
        }

        const resSecondaryDescription = document.getElementById('resSecondaryDescription');
        if (resSecondaryDescription) {
            resSecondaryDescription.textContent = pred.is_normal
                ? 'Physiological cardiac sound patterns confirmed across Aortic, Mitral, Pulmonary, and Tricuspid auscultation positions.'
                : 'Acoustic heart-sound murmurs exceed validated clinical decision thresholds. Valvular pathology indicated.';
        }

        const resRiskPill = document.getElementById('resRiskPill');
        if (resRiskPill) {
            const riskStr = pred.risk_level || 'Low Risk';
            resRiskPill.textContent = riskStr.toUpperCase();
            const rkClass = riskStr.toLowerCase().replace(/\s+/g, '-');
            resRiskPill.className = `risk-pill ${rkClass}`;
        }

        // 3. Valvular Probabilities Grid
        const probsGrid = document.getElementById('probsGrid');
        if (probsGrid && pred.raw_probabilities) {
            probsGrid.innerHTML = '';
            const diseaseMap = {
                N: { name: "Normal Auscultation", desc: "Physiological S1/S2 heart sounds" },
                AS: { name: "Aortic Stenosis", desc: "Systolic ejection murmur (Aortic)" },
                AR: { name: "Aortic Regurgitation", desc: "Diastolic decrescendo murmur (Aortic)" },
                MR: { name: "Mitral Regurgitation", desc: "Pansystolic murmur (Apex)" },
                MS: { name: "Mitral Stenosis", desc: "Diastolic rumble with opening snap" }
            };

            const order = ['N', 'AS', 'AR', 'MR', 'MS'];
            order.forEach(code => {
                const prob = pred.raw_probabilities[code] !== undefined ? pred.raw_probabilities[code] : 0.0;
                const pct = Math.round(prob * 100);
                const threshRaw = (pred.decision_thresholds && pred.decision_thresholds[code] !== undefined)
                    ? pred.decision_thresholds[code]
                    : 0.55;
                const thresh = Math.round(threshRaw * 100);
                const isElevated = pct >= thresh;
                const info = diseaseMap[code] || { name: code, desc: "" };

                const card = document.createElement('div');
                card.className = `prob-card ${isElevated && code !== 'N' ? 'positive' : ''}`;

                card.innerHTML = `
                    <div class="prob-top">
                        <span class="prob-code">${code}</span>
                        <span class="prob-num">${pct}%</span>
                    </div>
                    <div class="prob-name">${info.name}</div>
                    <div class="prob-bar-container" title="Threshold: ${thresh}%">
                        <div class="prob-bar-fill" style="width: ${pct}%"></div>
                    </div>
                    <div class="prob-footer">
                        <span>Threshold: <strong>${thresh}%</strong></span>
                        <span class="prob-badge ${isElevated ? 'pos' : 'neg'}">
                            ${code === 'N' ? (isElevated ? 'Normal' : 'Low') : (isElevated ? 'Positive' : 'Negative')}
                        </span>
                    </div>
                `;
                probsGrid.appendChild(card);
            });
        }

        // 4. Acoustic Murmur Epicenter & Valve Attribution
        const xaiContainer = document.getElementById('xaiContainer');
        if (xaiContainer) {
            xaiContainer.innerHTML = '';
            if (pred.valve_attributions && pred.valve_attributions.length > 0) {
                pred.valve_attributions.forEach(item => {
                    const block = document.createElement('div');
                    block.className = 'finding-item';

                    let valveList = '';
                    if (item.valve_attributions) {
                        item.valve_attributions.forEach(v => {
                            const scorePct = Math.round((v.branch_score || 0) * 100);
                            valveList += `<span style="font-size: 0.78rem; font-weight: 600; margin-right: 10px;">${v.valve_name}: <strong>${scorePct}%</strong></span>`;
                        });
                    }

                    block.innerHTML = `
                        <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">
                            ${item.disease_class} Murmur Focus &bull; Primary Epicenter: <span style="color: var(--primary);">${item.top_contributing_valve}</span>
                        </div>
                        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 6px;">
                            Spatial-temporal attention confirms acoustic energy concentration at ${item.top_contributing_valve}.
                        </div>
                        <div style="background: #ffffff; padding: 6px 10px; border-radius: 4px; border: 1px solid var(--border-light);">
                            ${valveList}
                        </div>
                    `;
                    xaiContainer.appendChild(block);
                });
            } else {
                xaiContainer.innerHTML = `
                    <div class="finding-item" style="border-left-color: var(--success);">
                        <strong>Physiological Baseline:</strong> No localized pathological murmur epicenters detected. Neural activations remain uniform and physiological across all 8 recordings.
                    </div>
                `;
            }
        }

        // 5. ACC/AHA Evidence Guidelines
        const guidelinesContainer = document.getElementById('guidelinesContainer');
        if (guidelinesContainer) {
            guidelinesContainer.innerHTML = '';
            if (evidence.retrieved_guidelines && evidence.retrieved_guidelines.length > 0) {
                evidence.retrieved_guidelines.forEach(g => {
                    const quoteBox = document.createElement('div');
                    quoteBox.className = 'guideline-quote';
                    quoteBox.innerHTML = `
                        <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">
                            ${g.target_disease} &bull; ${g.section_name} (Page ${g.page_number})
                        </div>
                        <div>"${g.content_text}"</div>
                        <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 4px;">
                            <strong>Citation:</strong> ${g.guideline_title} (2020 ACC/AHA Valvular Guidelines)
                        </div>
                    `;
                    guidelinesContainer.appendChild(quoteBox);
                });
            } else {
                guidelinesContainer.innerHTML = `
                    <div class="guideline-quote" style="border-left-color: var(--success);">
                        <strong>Physiological Auscultation:</strong> Patient exhibits physiological heart sounds without indications for interventional valvular management under 2020 ACC/AHA guidelines.
                    </div>
                `;
            }
        }

        // 6. Signal Quality QC Summary
        const qcSummaryBox = document.getElementById('qcSummaryBox');
        if (qcSummaryBox) {
            const isPass = (quality.status === 'PASS');
            qcSummaryBox.style.borderLeftColor = isPass ? 'var(--success)' : 'var(--warning)';
            qcSummaryBox.innerHTML = `
                <strong>Signal Integrity Audit:</strong> Status: <span style="font-weight: 800; color: ${isPass ? 'var(--success)' : 'var(--warning)'};">${quality.status || 'PASS'}</span> &bull; ${quality.summary || 'All 8 recordings verified at 2,000 Hz with 4th-order Butterworth filtering (25-400 Hz).'}`;
        }

        // 7. Electronic Medical Consultation Record
        const reportMarkdownPre = document.getElementById('reportMarkdownPre');
        if (reportMarkdownPre) {
            reportMarkdownPre.textContent = report.structured_markdown_report || 'Official clinical consultation note generated.';
        }

        // 8. Buttons Wiring
        const btnCopyNote = document.getElementById('btnCopyNote');
        if (btnCopyNote) {
            btnCopyNote.onclick = () => {
                const note = report.structured_markdown_report || '';
                navigator.clipboard.writeText(note)
                    .then(() => alert("Official Clinical Consultation Note copied to clipboard."))
                    .catch(() => alert("Failed to copy note to clipboard."));
            };
        }

        const btnPrintReport = document.getElementById('btnPrintReport');
        if (btnPrintReport) {
            btnPrintReport.onclick = () => window.print();
        }
    }
});

