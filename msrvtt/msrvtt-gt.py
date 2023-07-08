import cPickle
import h5py
#from __future__ import division
import ast
# vidlist=[]
# nounlist=[]
# verblist=[]
# with open('msrvtt_train_list', 'rb') as f:
#     msrvtt_my_list = cPickle.load(f)
# for (k, v, j) in msrvtt_my_list:
#     vidlist.append(k)
#     nounlist.append(v)
#     verblist.append(j)
# vidlist = vidlist
# nounlist = nounlist
# verblist = verblist
# num = len(vidlist)
# cnt =0.0
# for i in verblist:
#     if i==7:
#         cnt+=1
# acc = cnt/num
# for i in verblist:
#     if i==7:
#         cnt+=1
# acc = cnt/num
# print acc #0.285
# label = h5py.File('/root/autodl-tmp/GL-RG/data/metadata/msrvtt_train_sequencelabel.h5', 'r')
# length = label['label_length'][:]
# num = 0.0
# for i in length:
#     if i>=14:
#         num+=1
# acc = num/len(length)
# print acc
label = h5py.File('/root/autodl-tmp/GL-RG/data/metadata/msvd_train_sequencelabel.h5', 'r')
length = label['label_length'][:]
num = 0.0
for i in length:
    if i>=11:
        num+=1
acc = num/len(length)
print acc
# msrvtt_long = 22.8   14
# msvd_long = 22.2  11
# xt = self.embed(it) + self.length_level_embedding(lvl)
# current_input = torch.cat([visual_feats, xt], dim=-1)

