# -*- coding: UTF-8 -*-
import os
import sys
import time
import math
import json
import uuid
import logging
import numpy as np

import argparse
import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.optim as optim
from torch.nn.utils import clip_grad_norm

from datetime import datetime
from six.moves import cPickle

from dataloader import DataLoader
from model import CaptionModel, CrossEntropyCriterion, RewardCriterion, CrossEntropyCriterion2, CrossEntropyCriterion3, CrossEntropyCriterion4

import utils
import opts

sys.path.append("cider")
from pyciderevalcap.cider.cider import Cider
from pyciderevalcap.ciderD.ciderD import CiderD

sys.path.append('coco-caption')
from pycocoevalcap.bleu.bleu import Bleu
from pycocoevalcap.meteor.meteor import Meteor
from pycocoevalcap.rouge.rouge import Rouge

logger = logging.getLogger(__name__)


def check_model(model, opt, infos, infos_history):
    if opt.eval_metric == 'MSRVTT':
        current_score = infos['Bleu_4'] + \
                        infos['METEOR'] + infos['ROUGE_L'] + infos['CIDEr']
    else:
        current_score = infos[opt.eval_metric]

    # write the full model checkpoint as well if we did better than ever
    if current_score >= infos['best_score']:
        infos['best_score'] = current_score
        infos['best_iter'] = infos['iter']
        infos['best_epoch'] = infos['epoch']

        logger.info('>>> Found new best [%s] score: %f, at iter: %d, epoch %d', opt.eval_metric, current_score, infos['iter'], infos['epoch'])

        torch.save({'model': model.state_dict(), 'infos': infos, 'opt': opt}, opt.model_file)
        logger.info('Wrote checkpoint to: %s', opt.model_file)

    else:
        logger.info('>>> Current best [%s] score: %f, at iter %d, epoch %d', opt.eval_metric, infos['best_score'], infos['best_iter'], infos['best_epoch'])

    infos_history[infos['epoch']] = infos.copy()
    with open(opt.history_file, 'w') as of:
        json.dump(infos_history, of)
    logger.info('Updated history to: %s', opt.history_file)

#------------修改----------
def train(model, criterion, optimizer, train_loader, val_loader, opt, criterion2, criterion3, criterion4, rl_criterion=None ):
    infos = {'iter': 0, 'epoch': 0, 'start_epoch': 0, 'best_score': float('-inf'), 'best_iter': 0, 'best_epoch': opt.max_epochs}

    checkpoint_checked = False
    rl_training = False
    seq_per_img = train_loader.get_seq_per_img()
    infos_history = {}

    if os.path.exists(opt.start_from):
        # loading the same model file at a different experiment dir
        start_from_file = os.path.join(opt.start_from, os.path.basename(opt.model_file)) if os.path.isdir(opt.start_from) else opt.start_from
        logger.info('Loading state from: %s', start_from_file)
        checkpoint = torch.load(start_from_file)
        model.load_state_dict(checkpoint['model'])
        infos = checkpoint['infos']
        infos['start_epoch'] = infos['epoch']
        checkpoint_checked = True  # this epoch is already checked
    else:
        logger.info('No checkpoint found! Training from the scratch')

    if opt.use_rl == 1 and opt.use_rl_after == 0:
        opt.use_rl_after = infos['epoch']
        opt.use_it_after = infos['epoch']
        train_loader.set_current_epoch(infos['epoch'])

    while True:
        t_start = time.time()
        model.train()
        data = train_loader.get_batch()
        feats = [Variable(feat, volatile=False) for feat in data['feats']]
        labels = Variable(data['labels'], volatile=False)
        masks = Variable(data['masks'], volatile=False)
        #---------noun--------
        noun = Variable(data['noun'], volatile=False)
        verb = Variable(data['verb'], volatile=False)

        if torch.cuda.is_available():
            feats = [feat.cuda() for feat in feats]
            labels = labels.cuda()
            masks = masks.cuda()
            #-----noun--
            noun = noun.cuda()
            verb = verb.cuda()

        # implement scheduled sampling
        opt.ss_prob = 0
        if opt.use_ss == 1 and infos['epoch'] >= opt.use_ss_after:
            annealing_prob = opt.ss_k / (opt.ss_k + np.exp((infos['epoch'] - opt.use_ss_after) / opt.ss_k))
            opt.ss_prob = min(1 - annealing_prob, opt.ss_max_prob)
            model.set_ss_prob(opt.ss_prob)

        if opt.use_rl == 1 and infos['epoch'] >= opt.use_rl_after and not rl_training:
            logger.info('Using RL objective...')
            rl_training = True
            bcmr_scorer = {'Bleu_4': Bleu(), 'CIDEr': CiderD(df=opt.train_cached_tokens), 'METEOR': Meteor(), 'ROUGE_L': Rouge()}[opt.eval_metric]

        mixer_from = opt.mixer_from
        if opt.use_mixer == 1 and rl_training:
            # -1 for annealing
            if opt.mixer_from == -1:
                annealing_mixer = opt.seq_length - int(np.ceil((infos['epoch'] - opt.use_rl_after + 1) / float(opt.mixer_descrease_every)))
                mixer_from = max(1, annealing_mixer)

            model.set_mixer_from(mixer_from)

        dr_baseline_captions = opt.dr_baseline_captions
        if opt.use_it == 1 and rl_training:
            if opt.dr_baseline_captions == -1:
                annealing_robust = int(np.ceil((infos['epoch'] - opt.use_it_after + 1) / float(opt.dr_increase_every)))
                dr_baseline_captions = min(annealing_robust, seq_per_img - 1)

        optimizer.zero_grad()
        model.set_seq_per_img(seq_per_img)

        if rl_training or opt.use_dxe:
            # using mixer
            pred, model_res, logprobs = model(feats, labels)

            if opt.use_it == 0:
                # scst baseline in SCST paper
                scst_baseline, _ = model.sample([Variable(f.data, volatile=True) for f in feats], {'sample_max': 1, 'expand_feat': opt.expand_feat})

            if opt.use_it == 1:
                bcmrscores = data['bcmrscores']
                # compute discriminative cross-entropy or discrepant reward
                if opt.use_dxe:
                    # use discriminative cross-entropy (DXE)
                    reward, m_score, g_score = utils.get_discriminative_cross_entropy_scores(model_res, bcmrscores=bcmrscores)
                else:
                    # use discrepant reward (DR)
                    reward, m_score, g_score = utils.get_discrepant_reward(model_res, data['gts'], bcmr_scorer,
                                                                bcmrscores=bcmrscores,
                                                                expand_feat=opt.expand_feat,
                                                                seq_per_img=train_loader.get_seq_per_img(),
                                                                dr_baseline_captions=dr_baseline_captions,
                                                                dr_baseline_type=opt.dr_baseline_type,
                                                                use_eos=opt.use_eos,
                                                                use_mixer=opt.use_mixer
                                                                )
            else:
                # use scst baseline by default, compute self-critical reward
                reward, m_score, g_score = utils.get_self_critical_reward(model_res, scst_baseline, data['gts'], bcmr_scorer,
                                                                          expand_feat=opt.expand_feat,
                                                                          seq_per_img=train_loader.get_seq_per_img(),
                                                                          use_eos=opt.use_eos)

            loss = rl_criterion(model_res, logprobs, Variable(torch.from_numpy(reward).float().cuda(), requires_grad=False))

        else:
            # use cross-entropy (XE)
            #pred = model(feats, labels, noun)[0]
            #----noun--
            lambda1 = opt.lamba1
            lambda2 = opt.lamba2
            lambda3 = opt.lamba3
            lambda4 = opt.lamba4
            pred, pred2, pred3,pred4, _, _ = model(feats, labels, noun,verb)
            #loss = criterion(pred, labels[:, 1:], masks[:, 1:])
            #-------noun-------
            loss = lambda1 * criterion(pred, labels[:, 1:], masks[:, 1:]) \
                   + lambda2 * criterion2(pred2, labels[:, 1:], masks[:, 1:]) \
                   + lambda3 * criterion3(pred3, labels[:, 1:], masks[:, 1:]) \
                   + lambda4 * criterion4(pred4, labels[:, 1:], masks[:, 1:])


        loss.backward()
        clip_grad_norm(model.parameters(), opt.grad_clip)
        optimizer.step()
        if float(torch.__version__[:3]) > 0.5:
            infos['TrainLoss'] = loss.item()
        else:
            infos['TrainLoss'] = loss.data[0]
        infos['mixer_from'] = mixer_from
        infos['dr_baseline_captions'] = dr_baseline_captions

        if infos['iter'] % opt.print_log_interval == 0:
            elapsed_time = time.time() - t_start
            log_info = [('Epoch', infos['epoch']), ('Iter', infos['iter']), ('Loss', infos['TrainLoss'])]
            if rl_training or opt.use_dxe:
                log_info += [('Reward', np.mean(reward[:, 0])), ('{} (m)'.format(opt.eval_metric), m_score), ('{} (b)'.format(opt.eval_metric), g_score)]
            if opt.use_ss == 1:
                log_info += [('ss_prob', opt.ss_prob)]
            if opt.use_mixer == 1:
                log_info += [('mixer_from', mixer_from)]
            if opt.use_it == 1 and rl_training:
                log_info += [('dr_baseline_captions', dr_baseline_captions)]
            log_info += [('Time', elapsed_time)]
            logger.info('%s', '\t'.join(
                ['{}: {}'.format(k, v) for (k, v) in log_info]))

        infos['iter'] += 1

        if infos['epoch'] < train_loader.get_current_epoch():
            infos['epoch'] = train_loader.get_current_epoch()
            checkpoint_checked = False
            learning_rate = utils.adjust_learning_rate(opt, optimizer, infos['epoch'] - infos['start_epoch'])
            logger.info('===> Learning rate: %f: ', learning_rate)

        if (infos['epoch'] >= opt.save_checkpoint_from and infos['epoch'] % opt.save_checkpoint_every == 0 and not checkpoint_checked):
            # evaluate the validation performance
            results = validate(model, criterion, val_loader, opt)
            logger.info('Validation output: %s', json.dumps(results['scores'], indent=4, sort_keys=True))
            infos.update(results['scores'])

            check_model(model, opt, infos, infos_history)
            checkpoint_checked = True

        if (infos['epoch'] >= opt.max_epochs or infos['epoch'] - infos['best_epoch'] > opt.max_patience):
            logger.info('>>> Terminating...')
            break

    return infos


def language_eval(predictions, cocofmt_file, opt):
    logger.info('>>> Language evaluating ...')
    tmp_checkpoint_json = os.path.join(
        opt.model_file + str(uuid.uuid4()) + '.json')
    json.dump(predictions, open(tmp_checkpoint_json, 'w'))
    lang_stats = utils.language_eval(cocofmt_file, tmp_checkpoint_json)
    os.remove(tmp_checkpoint_json)
    return lang_stats


def validate(model, criterion, loader, opt):
    model.eval()
    loader.reset()

    num_videos = loader.get_num_videos()
    batch_size = loader.get_batch_size()
    num_iters = int(math.ceil(num_videos * 1.0 / batch_size))
    last_batch_size = num_videos % batch_size
    seq_per_img = loader.get_seq_per_img()
    model.set_seq_per_img(seq_per_img)

    loss_sum = 0
    logger.info('#num_iters: %d, batch_size: %d, seg_per_image: %d', num_iters, batch_size, seq_per_img)
    predictions = []
    gt_avglogps = []
    test_avglogps = []
    
    for ii in range(num_iters):
        data = loader.get_batch()
        with torch.no_grad():
            feats = [Variable(feat, volatile=True) for feat in data['feats']]
            if loader.has_label:
                labels = Variable(data['labels'], volatile=True)
                masks = Variable(data['masks'], volatile=True)
            if ii == (num_iters - 1) and last_batch_size > 0:
                feats = [f[:last_batch_size] for f in feats]
                if loader.has_label:
                    labels = labels[:last_batch_size * seq_per_img]  # labels shape is DxN
                    masks = masks[:last_batch_size * seq_per_img]


            if torch.cuda.is_available():
                feats = [feat.cuda() for feat in feats]
                if loader.has_label:
                    labels = labels.cuda()
                    masks = masks.cuda()

            # if loader.has_label:
            #     t_start = time.time()
                # pred, gt_seq, gt_logseq = model(feats, labels)
                # logger.info("Inference time: %f, batch_size: %d" % ((time.time() - t_start) / batch_size, batch_size))
                # if opt.output_logp == 1:
                #     gt_avglogp = utils.compute_avglogp(gt_seq, gt_logseq.data)
                #     gt_avglogps.extend(gt_avglogp)
                #
                # loss = criterion(pred, labels[:, 1:], masks[:, 1:])
                # if float(torch.__version__[:3]) > 0.5:
                #     loss_sum += loss.item()
                # else:
                #     loss_sum += loss.data[0]
            # 做修改
            t_start = time.time()#---修改
            seq, logseq = model.sample(feats, {'beam_size': opt.beam_size, 'control_id': opt.control_id})
            logger.info("Inference time: %f, batch_size: %d" % ((time.time() - t_start) / batch_size, batch_size))#-----修改
            
            sents = utils.decode_sequence(opt.vocab, seq)
            if opt.output_logp == 1:
                test_avglogp = utils.compute_avglogp(seq, logseq)
                test_avglogps.extend(test_avglogp)

            for jj, sent in enumerate(sents):
                if opt.output_logp == 1:
                    entry = {'image_id': data['ids'][jj], 'caption': sent, 'avglogp': test_avglogp[jj]}
                else:
                    entry = {'image_id': data['ids'][jj], 'caption': sent}
                predictions.append(entry)
                logger.debug('[%d] video %s: %s' % (jj, entry['image_id'], entry['caption']))

    # loss = round(loss_sum / num_iters, 3)
    results = {}
    lang_stats = {}

    if opt.language_eval == 1 and loader.has_label:
        logger.info('>>> Language evaluating ...')
        tmp_checkpoint_json = os.path.join(opt.model_file + str(uuid.uuid4()) + '.json')
        json.dump(predictions, open(tmp_checkpoint_json, 'w'))
        lang_stats = utils.language_eval(loader.cocofmt_file, tmp_checkpoint_json)
        os.remove(tmp_checkpoint_json)

    results['predictions'] = predictions
    # results['scores'] = {'Loss': -loss}
    # results['scores'].update(lang_stats)
    results['scores'] = lang_stats

    if opt.output_logp == 1:
        avglogp = sum(test_avglogps) / float(len(test_avglogps))
        results['scores'].update({'avglogp': avglogp})

        gt_avglogps = np.array(gt_avglogps).reshape(-1, seq_per_img)
        assert num_videos == gt_avglogps.shape[0]

        gt_avglogps_file = opt.model_file.replace('.pth', '_gt_avglogps.pkl', 1)
        cPickle.dump(gt_avglogps, open(gt_avglogps_file, 'w'), protocol=cPickle.HIGHEST_PROTOCOL)

        logger.info('Wrote GT logp to: %s', gt_avglogps_file)

    return results


def test(model, criterion, loader, opt):
    results = validate(model, criterion, loader, opt)
    logger.info('Test output: %s', json.dumps(results['scores'], indent=4))

    json.dump(results, open(opt.result_file, 'w'))
    logger.info('Wrote output caption to: %s ', opt.result_file)


if __name__ == '__main__':

    opt = opts.parse_opts() # 参数设置

    logging.basicConfig(level=getattr(logging, opt.loglevel.upper()), format='%(asctime)s:%(levelname)s: %(message)s')

    logger.info('Input arguments: %s', json.dumps(vars(opt), sort_keys=True, indent=4))

    # Set the random seed manually for reproducibility.
    np.random.seed(opt.seed)
    torch.manual_seed(opt.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(opt.seed)

    train_opt = {'label_h5': opt.train_label_h5,
                 'batch_size': opt.batch_size,
                 'feat_h5': opt.train_feat_h5,
                 'cocofmt_file': opt.train_cocofmt_file,
                 'bcmrscores_pkl': opt.train_bcmrscores_pkl,
                 'eval_metric': opt.eval_metric,
                 'seq_per_img': opt.train_seq_per_img,
                 'num_chunks': opt.num_chunks,
                 'use_resnet_feature': opt.use_resnet_feature,
                 'use_c3d_feature': opt.use_c3d_feature,
                 'use_audio_feature': opt.use_audio_feature,
                 'use_global_local_feature': opt.use_global_local_feature,
                 'use_long_range': opt.use_long_range,
                 'use_short_range': opt.use_short_range,
                 'use_local': opt.use_local,
                 'mode': 'train'
                 }

    val_opt = {'label_h5': opt.val_label_h5,
               'batch_size': opt.test_batch_size,
               'feat_h5': opt.val_feat_h5,
               'cocofmt_file': opt.val_cocofmt_file,
               'seq_per_img': opt.test_seq_per_img,
               'num_chunks': opt.num_chunks,
               'use_resnet_feature': opt.use_resnet_feature,
               'use_c3d_feature': opt.use_c3d_feature,
               'use_audio_feature': opt.use_audio_feature,
               'use_global_local_feature': opt.use_global_local_feature,
               'use_long_range': opt.use_long_range,
               'use_short_range': opt.use_short_range,
               'use_local': opt.use_local,
               'mode': 'test'
               }

    test_opt = {'label_h5': opt.test_label_h5,
                'batch_size': opt.test_batch_size,
                'feat_h5': opt.test_feat_h5,
                'cocofmt_file': opt.test_cocofmt_file,
                'seq_per_img': opt.test_seq_per_img,
                'num_chunks': opt.num_chunks,
                'use_resnet_feature': opt.use_resnet_feature,
                'use_c3d_feature': opt.use_c3d_feature,
                'use_audio_feature': opt.use_audio_feature,
                'use_global_local_feature': opt.use_global_local_feature,
                'use_long_range': opt.use_long_range,
                'use_short_range': opt.use_short_range,
                'use_local': opt.use_local,
                'mode': 'test'
                }

    train_loader = DataLoader(train_opt)
    val_loader = DataLoader(val_opt)
    test_loader = DataLoader(test_opt)

    opt.vocab = train_loader.get_vocab()
    opt.vocab_size = train_loader.get_vocab_size()
    opt.seq_length = train_loader.get_seq_length()
    opt.feat_dims = train_loader.get_feat_dims()
    opt.history_file = opt.model_file.replace('.pth', '_history.json', 1)

    logger.info('Building model...')
    model = CaptionModel(opt)

    xe_criterion = CrossEntropyCriterion()
    rl_criterion = RewardCriterion()
    #---------新增加---------
    xe_criterion2 = CrossEntropyCriterion2()
    xe_criterion3 = CrossEntropyCriterion3()
    xe_criterion4 = CrossEntropyCriterion4()

    if torch.cuda.is_available():
        model.cuda()
        xe_criterion.cuda()
        rl_criterion.cuda()
        #-------新增------
        xe_criterion2.cuda()
        xe_criterion3.cuda()
        xe_criterion4.cuda()

    logger.info('Start training...')
    start = datetime.now()

    optimizer = optim.Adam(model.parameters(), lr=opt.learning_rate)
    #---修改----
    infos = train(model, xe_criterion, optimizer, train_loader, val_loader, opt, xe_criterion2,xe_criterion3,xe_criterion4,rl_criterion=rl_criterion)
    logger.info(
        'Best val %s score: %f. Best iter: %d. Best epoch: %d',
        opt.eval_metric,
        infos['best_score'],
        infos['best_iter'],
        infos['best_epoch'])

    logger.info('Training time: %s', datetime.now() - start)

    if opt.result_file:
        logger.info('Start testing...')
        start = datetime.now()

        logger.info('Loading model: %s', opt.model_file)
        checkpoint = torch.load(opt.model_file)
        model.load_state_dict(checkpoint['model'])

        # test(model, xe_criterion, test_loader, opt)
        #-----------新增代码-----------
        logger.info('-' * 5 + 'origin result' + '-' * 5)
        opt.control_id = 0
        test(model, xe_criterion, test_loader, opt)
        logger.info('-' * 5 + 'short result' + '-' * 5)
        opt.control_id = 1
        test(model, xe_criterion, test_loader, opt)
        logger.info('-' * 5 + 'middle result' + '-' * 5)
        opt.control_id = 2
        test(model, xe_criterion, test_loader, opt)
        logger.info('-' * 5 + 'long result' + '-' * 5)
        opt.control_id = 3
        test(model, xe_criterion, test_loader, opt)
        logger.info('-' * 5 + 'single-object result' + '-' * 5)
        opt.control_id = 4
        test(model, xe_criterion, test_loader, opt)
        logger.info('-' * 5 + 'multi-object result' + '-' * 5)
        opt.control_id = 5
        test(model, xe_criterion, test_loader, opt)
        logger.info('-' * 5 + 'single-action result' + '-' * 5)
        opt.control_id = 6
        test(model, xe_criterion, test_loader, opt)
        logger.info('-' * 5 + 'multi-action result' + '-' * 5)
        opt.control_id = 7
        test(model, xe_criterion, test_loader, opt)

        #-----------------------------
        logger.info('Testing time: %s', datetime.now() - start)