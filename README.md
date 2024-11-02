# Overview 
In this repository, you will find a Python implementation of our PailGen. As described in our paper, PailGen is a novel automatic vulnerability patch generation approach that integrates retrieval-augmented fix pattern mining with in-context learning.
# Setting up the environment
You can set up the environment by following commands:
```
conda create -n RagFixer python=3.9.7
pip install transformers
pip install torch
pip install numpy
pip install tqdm
pip install pandas
pip install tokenizers
pip install datasets
pip install gdown
pip install tensorboard
pip install scikit-learn
pip install tree-sitter
pip install tree-sitter-c
pip install codebleu 
```
Alternatively, we provide requirements.txt with version of packages specified to ensure the reproducibility, you may install via the following commands:
```
pip install -r requirements.txt
```
# Data preprocess
```
python preprocess_data.py
```
After preprocessing dataset, you can obtain two .csv files, i.e., train.csv and test.csv.
# Generate fix patterns
```
cd fix_patterns
python generate_patterns.py
```
The above command generates fix patterns from the retrieved relevant vulnerability-fix cases. The file retrieved_results_bigvul_cvefixes_top50.json contains the retrieved results of our hybrid retriever. In this file, each vulnerable code sample includes the top 50 most relevant vulnerability-fix pairs. We follow [DPR](https://github.com/facebookresearch/DPR) to train and test our hybrid retriever.  
```
cd ..
python process_prompt_data.py
```
Execute the above command to obtain all components of the LLM's prompt.
# Patch generation
```
python llm_api_call_augment.py
```
The above command will generate candidate repair patches.
# Calculate metrics
```
python calculate_combined_metrics.py
```
# Acknowledgements
- Special thanks to authors of VulMaster ([Zhou et al.](https://dl.acm.org/doi/abs/10.1145/3597503.3639222))
- Special thanks to authors of TypeFix ([Peng et al.](https://arxiv.org/pdf/2306.01394))
- Special thanks to dataset providers of CVEFixes ([Bhandari et al.](https://dl.acm.org/doi/pdf/10.1145/3475960.3475985)), Big-Vul ([Fan et al.](https://dl.acm.org/doi/10.1145/3379597.3387501)), and D2A ([Zheng et al.](https://arxiv.org/pdf/2102.07995)).
