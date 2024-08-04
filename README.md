# SAVC
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
## Installation
First clone this repository

`git clone --recursive https://github.com/myccver/SAVC.git`

Then, please run following script to download Stanford CoreNLP 3.6.0 models into coco-caption/:

```
cd msrvtt/coco-caption
./get_stanford_models.sh
```
## Training
### MSR-VTT
```
cd msrvtt
sh train.sh
```

### MSVD
```
cd msvd
sh train.sh
```

## Testing
### MSR-VTT
```
cd msrvtt
sh test.sh
```
### MSVD
```
cd msvd
sh test.sh
```
