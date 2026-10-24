import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Info,
  ListOrdered,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import {
  getLatestDiagnostics,
  getLatestPrediction,
  getModelStatus,
} from '../api';
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  HealthGauge,
  LoadingState,
  StatusBadge,
} from '../components/common';
import type {
  DiagnosticReport,
  ModelStatusResponse,
  PredictionResult,
} from '../types';

export const HealthRiskView: React.FC = () => {
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [diagnostics, setDiagnostics] = useState<DiagnosticReport | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [pred, diag, model] = await Promise.all([
        getLatestPrediction().catch(() => null),
        getLatestDiagnostics().catch(() => null),
        getModelStatus().catch(() => null),
      ]);
      setPrediction(pred);
      setDiagnostics(diag);
      setModelStatus(model);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch health and risk analytics.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading && !prediction && !diagnostics) {
    return <LoadingState message="Evaluating ML anomaly inference and diagnostic report..." height={350} />;
  }

  if (error && !prediction) {
    return (
      <ErrorState
        title="Diagnostic Analysis Unavailable"
        message={error}
        detail="Capture a telemetry snapshot or start the background worker to populate feature vectors."
        onRetry={fetchData}
        height={300}
      />
    );
  }

  const score = prediction?.health_score ?? diagnostics?.overall_health_score ?? null;
  const risk = prediction?.risk_category ?? diagnostics?.risk_category ?? 'Unknown';
  const recommendations = diagnostics?.recommendations || [];

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="page-title">
            <ShieldCheck size={20} style={{ color: 'var(--accent-primary)' }} />
            <span>Health &amp; Failure Risk Analysis</span>
          </div>
          <div className="page-subtitle">
            Deterministic multi-signal health deductions, empirical anomaly inference, and automated remediation runbooks
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          icon={<RefreshCw size={13} />}
          loading={loading}
          onClick={fetchData}
        >
          Re-evaluate Risk
        </Button>
      </div>

      {/* Top Health & Model Status Split Grid */}
      <div className="grid-split-left">
        {/* Left: Deterministic Health Score Card */}
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Zap size={15} style={{ color: 'var(--accent-primary)' }} />
              <span>System Health Assessment</span>
            </div>
          }
          subtitle="Multi-signal weighted deduction model"
        >
          <div style={{ padding: '8px 0 4px 0', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <HealthGauge score={score} riskCategory={risk} size={150} />

            <div
              style={{
                width: '100%',
                marginTop: 16,
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 10,
              }}
            >
              <div
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'rgba(0, 0, 0, 0.25)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Anomaly Score
                </div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    color: (prediction?.anomaly_score ?? 0) >= 0.5 ? 'var(--status-critical)' : 'var(--accent-primary)',
                    marginTop: 3,
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {prediction ? prediction.anomaly_score.toFixed(3) : '--'}
                </div>
              </div>

              <div
                style={{
                  padding: '10px 12px',
                  backgroundColor: 'rgba(0, 0, 0, 0.25)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Risk Classification
                </div>
                <div style={{ marginTop: 5 }}>
                  <StatusBadge status={risk} />
                </div>
              </div>
            </div>

            {/* Warnings & Deduction Signals */}
            {prediction?.warnings && prediction.warnings.length > 0 && (
              <div
                style={{
                  width: '100%',
                  marginTop: 14,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                }}
              >
                <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Active Deduction Signals ({prediction.warnings.length})
                </div>
                {prediction.warnings.map((w, idx) => (
                  <div
                    key={idx}
                    style={{
                      fontSize: 12,
                      padding: '7px 10px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--status-warning-bg)',
                      border: '1px solid var(--status-warning-border)',
                      color: 'var(--status-warning)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                  >
                    <AlertTriangle size={13} style={{ flexShrink: 0 }} />
                    <span>{w}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Right: Active ML Model Status & Diagnostic Summary */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Diagnostic Headline Summary Card */}
          {diagnostics && (
            <div
              style={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-lg)',
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'center',
                gap: 16,
              }}
            >
              <div
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: diagnostics.critical_count > 0 ? 'var(--status-critical-bg)' : 'var(--status-healthy-bg)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                {diagnostics.critical_count > 0 ? (
                  <ShieldAlert size={22} style={{ color: 'var(--status-critical)' }} />
                ) : (
                  <CheckCircle2 size={22} style={{ color: 'var(--status-healthy)' }} />
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>
                  {diagnostics.summary_headline}
                </div>
                {diagnostics.primary_concern && (
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                    Primary Concern: <span style={{ color: '#FCA5A5', fontWeight: 600 }}>{diagnostics.primary_concern}</span>
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                <span className="status-badge critical">{diagnostics.critical_count} Critical</span>
                <span className="status-badge warning">{diagnostics.warning_count} Warnings</span>
              </div>
            </div>
          )}

          {/* Model Estimator Details */}
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <Brain size={15} style={{ color: 'var(--accent-primary)' }} />
                <span>Isolation Forest Estimator Status</span>
              </div>
            }
            subtitle="Machine learning inference pipeline metadata"
          >
            {modelStatus ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                      {modelStatus.model_name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      Execution Mode: <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{modelStatus.mode}</span>
                    </div>
                  </div>
                  <StatusBadge
                    status={modelStatus.is_trained ? 'TRAINED ESTIMATOR' : 'HEURISTIC FALLBACK'}
                    type={modelStatus.is_trained ? 'healthy' : 'warning'}
                  />
                </div>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: 12,
                    padding: '12px 14px',
                    backgroundColor: 'rgba(0, 0, 0, 0.25)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: 12,
                  }}
                >
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>Model Version</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>
                      v{modelStatus.version}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>Input Dimensions</div>
                    <div style={{ fontWeight: 600, color: 'var(--accent-primary)', marginTop: 2 }}>
                      {modelStatus.expected_features} Engineered Features
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>Training Corpus</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>
                      {modelStatus.training_samples_count ?? 'Synthetic Baseline'} Samples
                    </div>
                  </div>
                </div>

                {/* Hyperparameters pill list */}
                {modelStatus.hyperparameters && Object.keys(modelStatus.hyperparameters).length > 0 && (
                  <div>
                    <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                      Active Hyperparameters
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {Object.entries(modelStatus.hyperparameters).map(([k, v]) => (
                        <span
                          key={k}
                          style={{
                            fontSize: 11,
                            backgroundColor: 'rgba(30, 41, 59, 0.7)',
                            color: '#CBD5E1',
                            padding: '3px 8px',
                            borderRadius: 4,
                            border: '1px solid #334155',
                          }}
                        >
                          {k}: <strong style={{ color: 'var(--accent-primary)' }}>{String(v)}</strong>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <EmptyState message="No model metadata available." height={140} />
            )}
          </Card>
        </div>
      </div>

      {/* Explainable Diagnostic Evidence & Remediation Steps */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Search size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Explainable Diagnostic Evidence &amp; Remediation Runbooks</span>
          </div>
        }
        subtitle="Empirically backed telemetry correlations with prioritized remediation steps"
      >
        {recommendations.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {recommendations.map((rec) => (
              <div
                key={rec.id}
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.25)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 18px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                }}
              >
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                        {rec.title}
                      </span>
                      <StatusBadge status={rec.severity} />
                      {rec.target_component && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          Target Component: <strong style={{ color: 'var(--text-secondary)' }}>{rec.target_component}</strong>
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 4 }}>
                      {rec.summary}
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: 'var(--text-muted)',
                      textTransform: 'uppercase',
                      padding: '3px 8px',
                      borderRadius: 4,
                      backgroundColor: 'rgba(30, 41, 59, 0.8)',
                      border: '1px solid var(--border-subtle)',
                      letterSpacing: 0.5,
                    }}
                  >
                    {rec.category}
                  </span>
                </div>

                {/* Root Cause Hypothesis */}
                {rec.root_cause_hypothesis && (
                  <div
                    style={{
                      padding: '9px 12px',
                      backgroundColor: 'rgba(56, 189, 248, 0.06)',
                      border: '1px solid rgba(56, 189, 248, 0.22)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 12,
                      color: '#E0F2FE',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                  >
                    <Info size={14} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                    <span>
                      <strong>Root Cause Hypothesis:</strong> {rec.root_cause_hypothesis}
                    </span>
                  </div>
                )}

                {/* Evidence Table */}
                {rec.evidence && rec.evidence.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                      Supporting Telemetry Evidence
                    </div>
                    <div className="op-table-wrapper">
                      <table className="op-table" style={{ minWidth: 680 }}>
                        <thead>
                          <tr>
                            <th>Metric Indicator</th>
                            <th>Observed Value</th>
                            <th>Threshold Boundary</th>
                            <th>Severity</th>
                            <th>Diagnostic Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rec.evidence.map((ev, evIdx) => (
                            <tr key={evIdx}>
                              <td style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>{ev.metric_name}</td>
                              <td>{String(ev.observed_value)}</td>
                              <td><code style={{ fontSize: 11 }}>{ev.threshold}</code></td>
                              <td><StatusBadge status={ev.level} /></td>
                              <td style={{ color: 'var(--text-secondary)' }}>{ev.description}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Remediation Steps Runbook */}
                {rec.remediation_steps && rec.remediation_steps.length > 0 && (
                  <div>
                    <div
                      style={{
                        fontSize: 10.5,
                        fontWeight: 700,
                        color: 'var(--status-healthy)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 5,
                        marginBottom: 6,
                        textTransform: 'uppercase',
                        letterSpacing: 0.5,
                      }}
                    >
                      <ListOrdered size={14} />
                      <span>Prioritized Remediation Actions</span>
                    </div>
                    <ol
                      style={{
                        paddingLeft: 20,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 5,
                        fontSize: 12.5,
                        color: 'var(--text-primary)',
                      }}
                    >
                      {rec.remediation_steps.map((step, sIdx) => (
                        <li key={sIdx}>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Nominal Operating Baseline"
            message="No active critical deductions or anomaly recommendations found for the current host state."
            height={160}
          />
        )}
      </Card>
    </div>
  );
};
