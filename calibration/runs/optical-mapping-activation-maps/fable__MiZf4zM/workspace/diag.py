import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
mean_img=np.load('/tmp/mean_img.npy'); std_img=np.load('/tmp/std_img.npy'); tr=np.load('/tmp/trace.npy')
fig,ax=plt.subplots(2,2,figsize=(12,10))
im=ax[0,0].imshow(mean_img,cmap='gray'); ax[0,0].set_title('mean'); plt.colorbar(im,ax=ax[0,0])
im=ax[0,1].imshow(std_img,cmap='viridis'); ax[0,1].set_title('std'); plt.colorbar(im,ax=ax[0,1])
im=ax[1,0].imshow(std_img/np.maximum(mean_img,1),cmap='viridis'); ax[1,0].set_title('std/mean'); plt.colorbar(im,ax=ax[1,0])
ax[1,1].plot(-tr[:1500]); ax[1,1].set_title('inverted field mean, first 1500 frames')
plt.tight_layout(); plt.savefig('/tmp/diag1.png',dpi=70)
