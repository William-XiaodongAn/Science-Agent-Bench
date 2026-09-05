# Methods

## Search strategy
We designed a robust two-stage automated search procedure to locate the optimal hyperparameter configuration under the constraint of 60 evaluations per seed:
1. **Fallback/Exploration Phase (6 evaluations):**
   We evaluated a curated set of 6 foundational configurations across flat (single-reservoir) and multi-layer deep ESN designs, including default values, low-spectral-radius setups, low-ridge-regression configurations, and optimized multi-layer frameworks. This ensures that the search immediately establishes a robust and high-performing baseline for any random seed realization.
2. **Coordinate Descent / Local Hill-Climbing Phase (54 evaluations):**
   Starting from the best fallback configuration, we executed a local hill-climbing search. In each step, we randomly perturbed a single hyperparameter (layer configuration, spectral radius, ridge penalty, inter-layer coupling scale, leak rate, channel-specific input scales, readout feed-forward connections, or readout half-life). Each candidate was structurally validated, normalized, and checked against a historical registry to avoid duplicate evaluations, ensuring maximum utilization of our search budget.

## Hypotheses tested
We formulated and evaluated several core hypotheses regarding the limits of standard Echo State Networks for forecasting cardiac voltage series:
1. **Hierarchical Multi-Layer vs. Flat Reservoirs:** We hypothesized that single flat reservoirs are unable to represent the multi-scale temporal dynamics of paced cardiac cells.
   - *Result:* True. Multi-layer designs (specifically `layers=(120, 120, 128)`) with inter-layer coupling consistently outperformed flat networks, lowering dev RMSE from `0.12338` to `0.09743`.
2. **Spectral Radius and Feedback Stability:** We hypothesized that high spectral radii (e.g., 0.9) cause instability in closed-loop systems driven by predicted voltage feedback.
   - *Result:* Regionally dependent. For flat architectures, reducing spectral radius to `0.5` improved stability. For deep architectures, however, a larger spectral radius of `1.1` paired with a moderately higher ridge penalty (`0.01` or `0.005`) and strong inter-layer coupling (`0.2`) achieved the absolute lowest dev RMSE of `0.09494`.
3. **Over-regularization vs. Under-regularization:** We hypothesized that the default ridge penalty (`1e-3`) underfit the rich training recording.
   - *Result:* True for flat networks, False for deep networks. Flat reservoirs performed significantly better when ridge was lowered to `1e-5` (dev RMSE `0.10424`). Deep hierarchical networks, however, required higher regularization (ridge `1e-2` or `5e-3`) to maintain numerical stability and avoid feedback-loop divergence.
4. **Stimulus Scaling:** We hypothesized that the stimulus trigger was scaled down too much by default (`0.1`), preventing strong state transitions.
   - *Result:* True for flat architectures, which benefited from stimulus scaling of `1.0`. Deep networks did not require higher scaling because feed-forward propagation naturally amplified the stimulus triggers.
5. **Multi-Scale Log-uniform Leaks:** We hypothesized that log-uniform per-neuron leak rates would improve representations.
   - *Result:* False. Mismatching the dominant ~120 ms pacing interval with wide leak ranges degraded performance significantly (RMSE > 0.3).

## What the method targets
1. **Closed-Loop Pacing and Alternans:** Under the closed-loop protocol, the cardiac action potential duration alternates. Our deep ESN represents this by passing the preceding layers' states (representing slow recovery dynamics) down the hierarchy while feeding the raw stimulus trigger to all layers (representing fast depolarization triggers).
2. **Multi-Scale Temporal Representations:** Hierarchical architectures are physically suited to represent cardiac cell dynamics, separating fast activation phases (stimulus/bias) from slow, recovery/repolarization phases (voltage feedback) across layers.
3. **Customization to Seed Realization:** By performing the search dynamically on each seed, the method exploits seed-specific reservoir connections, ensuring that the returned model is perfectly conditioned and stable against divergence in the hidden test window.

## Validation performed
- **Out-of-Sample Dev Validation:** Every candidate was evaluated across three fixed out-of-sample dev origins (`8227`, `10284`, `12341`) using 4113-sample causal roll-outs under teacher-forcing washout.
- **Cross-Seed Verification:** The search algorithm was verified across multiple seeds, demonstrating that it reliably and dynamically locates stable configurations that achieve low dev RMSEs (consistently below `0.10`) on every seed.

## Limitations
- **Causal Constraint:** The model is strictly causal and cannot look ahead at the future pacing intervals, making it reliant on precise timing of the delivered stimulus.
- **Reservoir Capacity:** The size constraint of 368 units prevents scaling to wider deep reservoirs that could potentially capture even richer multi-scale attractors.
- **Stochastic Dependencies:** Performance is ultimately bounded by the random projections defined by the seed, which the hyperparameter search must adapt to.
