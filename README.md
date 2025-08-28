# The Community Index (C-Index)

This repository contains the code and sample data for the paper **"The Community Index: A More Comprehensive Approach to Assessing Scholarly Impact,"** available on arXiv.

The C-Index is a metric designed to quantify the diversity of a researcher's collaborative network across gender, geography, and academic discipline. It includes a "novelty multiplier" to reward the formation of new scientific partnerships.

## Repository Contents

*   `CIndex_Implementation.ipynb`: A Jupyter Notebook containing the full Python code for the C-Index calculation and report generation.
*   `sampleTableV3.csv`: Sample data formatted for use with the notebook.

## How to Use

This code serves as a reference implementation of the C-Index framework. You can use it to:

1.  **Understand the Methodology:** Explore the `calculateCIndex` function in the notebook to see the step-by-step logic behind the metric.
2.  **Reproduce Our Results:** Run the notebook with the provided sample data to generate the tables presented in our paper.
3.  **Analyze Your Own Data:** Adapt the notebook to run on your own bibliometric datasets. Simply format your data to match the columns in `sampleTableV3.csv`.

### Quickstart

1.  **Prerequisites:**
    ```bash
    pip install pandas networkx jupyter
    ```
2.  **Run:**
    Launch the Jupyter Notebook and execute the cells. The notebook is self-contained and will use the sample CSV to produce a final output table.

## Citation

Our paper is currently available as a pre-print on arXiv. If you use this work, please cite:

*Kumar, A., Sabet, C., Hammond, A., Fiske, A., et al. (2024). The Community Index: A More Comprehensive Approach to Assessing Scholarly Impact. arXiv preprint arXiv:[XXXX.XXXXX].*

```bibtex
@misc{kumar2024community,
      title={The Community Index: A More Comprehensive Approach to Assessing Scholarly Impact}, 
      author={Arav Kumar and Cameron Sabet and Alessandro Hammond and Amelia Fiske and Bhav Jain and Deirdre Goode and Dharaa Suresha and Leo Anthony Celi and Lisa Soleymani Lehmann and Ned Mccague and Rawan Abulibdeh and Sameer Pradhan},
      year={2024},
      eprint={[16519]},
      archivePrefix={arXiv},
      primaryClass={cs.DL}
}
```
