import os
import glob
from docx import Document

downloads = '/mnt/c/Users/Administrator/Downloads'
docx_files = glob.glob(downloads + '/EdgeClaw*.docx')

if docx_files:
    doc = Document(docx_files[0])
    
    output_path = '/mnt/c/Users/Administrator/.qclaw/workspace/edgeclaw_report.txt'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for para in doc.paragraphs:
            f.write(para.text + '\n')
    
    print('Saved to:', output_path)
else:
    print('No docx found')
