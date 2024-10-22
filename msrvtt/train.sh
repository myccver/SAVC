python msrvtt/train.py --train_label_h5 data/metadata/msrvtt_train_sequencelabel.h5 \
--val_label_h5 data/metadata/msrvtt_val_sequencelabel.h5 \
--test_label_h5 data/metadata/msrvtt_test_sequencelabel.h5 \
--train_cocofmt_file data/metadata/msrvtt_train_cocofmt.json \
--val_cocofmt_file data/metadata/msrvtt_val_cocofmt.json \
--test_cocofmt_file data/metadata/msrvtt_test_cocofmt.json \
--train_bcmrscores_pkl data/metadata/msrvtt_train_evalscores.pkl \
--train_feat_h5 "" "" "" data/feature/msrvtt_train_gl_feats.h5 \
--val_feat_h5 "" "" "" data/feature/msrvtt_val_gl_feats.h5 \
--test_feat_h5 "" "" "" data/feature/msrvtt_test_gl_feats.h5 \
--max_epochs 30 \
--train_seq_per_img 20 \
--test_seq_per_img 20 \
--batch_size 12 \
--test_batch_size 32 \
--learning_rate 0.0002 \
--lr_update 200 \
--save_checkpoint_from 1 \
--num_chunks 1 \
--train_cached_tokens data/metadata/msrvtt_train_ciderdf.pkl \
--use_rl 0 \
--use_mixer 0 \
--dr_baseline_captions 0 \
--dr_baseline_type 0 \
--loglevel INFO \
--model_file output/GL-RG_XE_msrvtt/msrvtt_0.pth \
--start_from No \
--result_file output/GL-RG_XE_msrvtt/msrvtt_0.json \
--control_id 0 \
--lamba2 1.2