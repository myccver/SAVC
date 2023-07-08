# Control-CG
Official code for Controllable Video Captioning with Learned Style Embeddings.
## Dependencies
- Python 2.7
- Pytorch
- Microsoft COCO Caption Evaluation
- CIDEr
- numpy, scikit-image, h5py, requests

You can use anaconda or miniconda to install the dependencies:

```
conda create -n control python=2.7 pytorch=1.0 scikit-image h5py requests
conda activate control
```
## Training
`python msrvtt/train.py --train_label_h5
data/metadata/msrvtt_train_sequencelabel.h5
--val_label_h5
data/metadata/msrvtt_val_sequencelabel.h5
--test_label_h5
data/metadata/msrvtt_test_sequencelabel.h5
--train_cocofmt_file
data/metadata/msrvtt_train_cocofmt.json
--val_cocofmt_file
data/metadata/msrvtt_val_cocofmt.json
--test_cocofmt_file
data/metadata/msrvtt_test_cocofmt.json
--train_bcmrscores_pkl
data/metadata/msrvtt_train_evalscores.pkl
--train_feat_h5
""
""
""
data/feature/msrvtt_train_gl_feats.h5
--val_feat_h5
""
""
""
data/feature/msrvtt_val_gl_feats.h5
--test_feat_h5
""
""
""
data/feature/msrvtt_test_gl_feats.h5
--beam_size
5
--rnn_size
512
--eval_metric
CIDEr
--language_eval
1
--max_epochs
30
--train_seq_per_img
20
--test_seq_per_img
20
--batch_size
12
--test_batch_size
32
--learning_rate
0.0002
--lr_update
200
--save_checkpoint_from
1
--num_chunks
1
--train_cached_tokens
data/metadata/msrvtt_train_ciderdf.pkl
--use_rl
0
--use_mixer
0
--mixer_from
-1
--use_it
0
--dr_baseline_captions
0
--dr_baseline_type
0
--loglevel
INFO
--use_eos
0
--use_long_range
1
--use_short_range
1
--use_local
1
--model_file
output/GL-RG_XE_msrvtt/msrvtt_0.pth
--start_from
No
--result_file
output/GL-RG_XE_msrvtt/msrvtt_0.json
--control_id
0
--lamba2
1.2
--input_encoding_size
512`
