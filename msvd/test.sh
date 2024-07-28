python msvd/test.py --model_file output/GL-RG_XE_msvd/msvd_0.pth \
--test_label_h5 data/metadata/msvd_test_sequencelabel.h5 \
--test_cocofmt_file data/metadata/msvd_test_cocofmt.json \
--test_feat_h5 "" "" "" data/feature/msvd_test_gl_feats.h5 \
--language_eval 1 \
--test_seq_per_img 17 \
--test_batch_size 32 \
--loglevel INFO \
--result_file output/GL-RG_XE_msvd/test_result0.json \
--control_id 0