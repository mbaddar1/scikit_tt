import numpy as np

import scikit_tt.data_driven.transform as tdt
from scikit_tt.data_driven import tgedmd
from systems import LemonSlice

from pyemma.msm import timescales_msm
from pyemma.coordinates import assign_to_centers




"""  System Settings: """
# Number of dimensions:
d = 4
# Diffusion constant:
beta = 1.0
# Spring constant for harmonic parts of the potential
alpha = 10.0
# Pre-factor for Lemon Slice:
c = 1.0
# Number of minima for Lemon Slice:
k = 4

""" Computational Settings: """
# Directory for results:
directory = "/Users/fkn1/Documents/Uni/Data/tgEDMD_Paper/LemonSlice/"
# Integration time step:
dt = 1e-3
# Number of time steps:
m = 300000
m_tgedmd = 3000
delta = int(round(m / m_tgedmd))
# Number of independent simulations:
ntraj = 10
# Set ranks of SVDs:
rank_list = [50, 100, 200, 300]
# Number of timescales to record:
nits = 3
# Lag times for MSM construction:
lags_msm = np.array([5, 10, 20, 50, 100, 200, 500])

""" Definition of Gaussian basis functions """
mean_ls = np.arange(-1.2, 1.21, 0.4)
sig_ls = 0.4
mean_quad = np.arange(-1.0, 1.01, 0.5)
sig_quad = 0.5

basis_list = []
for i in range(2):
    basis_list.append([tdt.GaussFunction(i, mean_ls[j], sig_ls) for j in range(len(mean_ls))])
for i in range(2, 4):
    basis_list.append([tdt.GaussFunction(i, mean_quad[j], sig_quad) for j in range(len(mean_quad))])


""" Run Simulation """
print('Running Simulations ...')
data = np.zeros((ntraj, d, m))
data_tgedmd = np.zeros((ntraj, d, m_tgedmd))
LS = LemonSlice(k, beta, c=c, d=d, alpha=alpha)
for ii in range(ntraj):
    print("Simulating trajectory %d..."%ii)
    x0 = np.random.rand(d)
    ii_traj = LS.simulate(x0, m, dt)
    data[ii, :, :] = ii_traj
    data_tgedmd[ii, :, :] = ii_traj[:, ::delta]
    print("Complete.")

print("Saving Data...")
np.save(directory + "Simulation_LS_delta_%d.npy"%delta, data_tgedmd)
print("Done.")
print(" ")

""" Run tgEDMD """
timescales = np.zeros((ntraj, len(rank_list), nits))
eigfuns = np.zeros((ntraj, len(rank_list), nits+1, m_tgedmd))
for ii in range(ntraj):
    print("Analyzing data for trajectory %d..."%ii)
    diffusion = np.zeros((data_tgedmd.shape[1], data_tgedmd.shape[1], data_tgedmd.shape[2]))
    for k in range(diffusion.shape[2]):
        diffusion[:, :, k] = LS.diffusion(data_tgedmd[ii, :, k])

    # AMUSEt for the reversible case
    qq = 0
    for rank in rank_list:
        eigvals, traj_eigfuns = tgedmd.amuset_hosvd_reversible(data_tgedmd[ii, :, :], basis_list, diffusion,
                                                               num_eigvals=5, return_option='eigenfunctionevals',
                                                               threshold=0.0, max_rank=rank)
        timescales[ii, qq, :] = [-1.0 / kappa for kappa in eigvals[1:nits+1]]
        eigfuns[ii, qq, :, :] = traj_eigfuns[:nits+1, :]
        print('Implied time scales for rank = %d : '%rank, timescales[qq, :])
        qq += 1
    print(" ")

# Save Results:
dic = {}
dic["ranks"] = rank_list
dic["timescales"] = timescales
dic["eigfuns"] = eigfuns
np.savez_compressed(directory + "Results_LS.npz", **dic)

""" Build MSM as reference: """
# Discretize the data:
xe = np.arange(-1.8, 1.81, 0.25)
xc = 0.5 * (xe[:-1] + xe[1:])
X, Y = np.meshgrid(xc, xc)
XC = np.hstack((X.flatten()[:, None], Y.flatten()[:, None]))

# Calculate MSM timescales for all simulations and lag times:
ts_msm = np.zeros((ntraj, len(lags_msm), nits))
for ii in range(ntraj):
    dtraj = assign_to_centers(data[ii, :2, :].T, XC)
    its = timescales_msm(dtraj, lags=lags_msm, nits=nits)
    ts_msm[ii, :, :] = dt * its.timescales

# Save results:
dic = {}
dic["lags_msm"] = dt * lags_msm
dic["centers"] = XC
dic["timescales"] = ts_msm
np.savez_compressed(directory + "MSM_LS.npz", **dic)


