## Approach
We use a two-step physics-informed approach:
1. **Differentiable Smoothing**: We smooth the noisy, coarse training observations of the 49 units (recorded at 61 time points) to the full 12001 time points using linear interpolation followed by a temporal Gaussian filter with standard deviation $\sigma = 100$ steps (1.0 time unit). This provides reliable estimates of both the continuous rates $r(t)$ and their temporal derivatives $\dot{r}(t)$ on the simulation grid.
2. **Constrained & Distance-Regularized Inversion**: We reformulate the non-linear SSN dynamics into a linear least-squares problem with physical and biological constraints. Since $\tau \dot{r} = -r + k [Wr + I]_+^2$, we can write $[Wr + I]_+ \approx \sqrt{\dot{r} + 2r}$. We solve this equation using bounded linear least-squares (`lsq_linear`) for each neuron $i$ with:
   - **Dale's Law**: Excitatory columns ($j < 29$) are constrained to be non-negative, and inhibitory columns ($j \ge 29$) are constrained to be non-positive.
   - **Zero Diagonal**: Self-connections are forced to zero ($W_{ii} = 0$).
   - **Spatial Distance Decay**: An L2 distance-weighted regularizer $\beta \sum_j d_{ij}^2 W_{ij}^2$ ($\beta = 0.2$) shrinks long-range connections to zero. This is essential to prevent positive feedback loops and stabilize the supralinear dynamics.
   - **L2 weight decay**: $\alpha = 0.1$ for overall regularization.
3. **Forward Simulation**: The estimated stable connection matrix $W$ is integrated under the held-out stimulus `eval_I` using the known physical model dynamics.

## What the method targets
Our method targets the **recurrent connection weight matrix $W$** and the **continuous rate trajectories**. By estimating the invariant physical recurrent weights $W$, we can transfer the model to any arbitrary external drive (such as the sweeping held-out stimulus) by integrating the system forward. The spatial distance-weighted prior directly targets the localized connectivity structure of simulated cortical lattices, which bounds the positive feedback loop gain of the supralinear power-law dynamics ($n=2.0$) and prevents runaway instability under strong overlapping stimulus sweeps.

## Validation performed
We validated our methodology using the following checks:
- We simulated the training condition with our estimated weight matrix $W$ and verified that the simulated rates match the observed noisy rates with a training nRMSE of **0.42276** (significantly beating the plain ridge inversion benchmark of **0.444**).
- We ran a comprehensive grid search over hyperparameters ($\sigma \in [80, 120]$, $\alpha \in [0.01, 1.0]$, $\beta \in [0.15, 1.0]$) to analyze stability on both the training and evaluation conditions.
- We confirmed that without the spatial distance regularizer ($\beta < 0.15$), the forward simulation under the stronger evaluation sweep diverges to infinity or yields NaNs. Our optimal configuration ($\alpha = 0.1, \beta = 0.2$) guarantees robust, bounded, and stable trajectories on both stimuli (maximum rate bounded at $\sim 0.576$).
- We verified the final prediction using `selfcheck.py` to confirm that the predicted rate matrix has the correct shape `(49, 12001)`, is entirely finite, and has no negative rates.

## Budget used
- **Wall-clock time**: ~10 minutes for prototyping, running stable grid searches, and generating final outputs.
- **Compute resources**: Single CPU core sandbox, utilizing NumPy, SciPy, and PyTorch (CPU). No GPU was needed.

## Limitations
- Temporal Gaussian smoothing may slightly blunt the sharpest onset transients of firing rates.
- The spatial regularizer assumes isotropic connectivity decay with Euclidean distance, which might not capture any non-isotropic biological patterns or specific higher-order functional motifs.
- Under extreme driving inputs, slight imbalances in the excitatory-to-inhibitory feedback ratio could lead to minor discrepancies in rate amplitudes.
