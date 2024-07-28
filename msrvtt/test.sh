python msrvtt/test.py --model_file output/GL-RG_XE_msrvtt/msrvtt_0.pth \
--test_label_h5 data/metadata/msrvtt_test_sequencelabel.h5 \
--test_cocofmt_file data/metadata/msrvtt_test_cocofmt.json \
--test_feat_h5 "" "" "" data/feature/msrvtt_test_gl_feats.h5 \
--test_seq_per_img 20 \
--test_batch_size 64 \
--loglevel INFO \
--result_file output/GL-RG_XE_msrvtt/msrvtt_0.json \
--control_id 0