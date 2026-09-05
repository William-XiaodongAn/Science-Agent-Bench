import torch
import time

device = torch.device("cpu")
N = 49
n_steps = 12001

W = torch.zeros((N, N), requires_grad=True, device=device)
r0 = torch.zeros(N, requires_grad=True, device=device)
I = torch.randn(N, n_steps, device=device)

start = time.time()
r = r0
r_list = [r]
dt_tau = 0.02
for t in range(n_steps - 1):
    # SSN rate equation
    # tau * dr/dt = -r + k * ( [ W*r + I(t) ]_+ )^n
    # r(t+1) = max(0, r(t) + dt/tau * ( -r(t) + k * relu( W @ r(t) + I(t) )^2 ) )
    # Note: rates are clipped at 0 at each step as per description
    input_to_units = torch.matmul(W, r) + I[:, t]
    ss_rate = 0.5 * torch.pow(torch.clamp(input_to_units, min=0.0), 2)
    dr_dt = -r + ss_rate
    r_next = r + dt_tau * dr_dt
    r = torch.clamp(r_next, min=0.0)
    if t % 200 == 0:
        r_list.append(r)

r_obs = torch.stack(r_list, dim=1)
loss = torch.sum(r_obs ** 2)
loss.backward()
end = time.time()

print("Time taken for one FWD+BWD pass of 12000 steps:", end - start, "seconds")
print("W grad norm:", W.grad.norm().item())
