import numpy as np, time
t=time.time()
fn='data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat'
raw=np.fromfile(fn,dtype='<u2',offset=1024)
nf=raw.size//(128*128+4); print('frames',nf, raw.size%(128*128+4))
raw=raw.reshape(nf,128*128+4)
foot=raw[:,-4:]; print('footer first rows',foot[:3], foot[-2:])
fr=raw[:,:128*128].reshape(nf,128,128).transpose(0,2,1)  # transpose each frame
print('frame0 mean',fr[0].mean(),'frame1 mean',fr[1].mean(),'frame2',fr[2].mean())
fr=fr[1:].astype(np.float32)
mean_img=fr.mean(0); std_img=fr.std(0)
print('mean img pct',np.percentile(mean_img,[1,5,25,50,75,95,99]))
print('std img pct',np.percentile(std_img,[1,5,25,50,75,95,99]))
np.save('/tmp/mean_img.npy',mean_img); np.save('/tmp/std_img.npy',std_img)
# field mean over bright pixels
m0=mean_img>np.percentile(mean_img,60)
tr=fr[:,m0].mean(1)
np.save('/tmp/trace.npy',tr)
print('trace first 400', np.round(tr[:400:10],1))
# derivative stats: fast upstroke vs slow repol => skewness of derivative
d=np.diff(tr); print('deriv skew', ((d-d.mean())**3).mean()/d.std()**3, 'min',d.min(),'max',d.max())
print('elapsed',time.time()-t)
