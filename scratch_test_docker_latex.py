import subprocess
import os
import tempfile

def test_docker_compile():
    latex_code = r"""
\documentclass{article}
\begin{document}
Hello from FresherFlow Docker LaTeX Compiler!
\end{document}
"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        tex_path = os.path.join(temp_dir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_code)
            
        print(f"Created temp tex file at {tex_path}")
        print("Running pdflatex in Docker container...")
        
        # We use a lightweight and popular latex docker image
        # 'paperist/texlive-ja:latest' is about 600MB or similar, or 'blang/latex:ubuntu'
        # Let's use 'blang/latex' or 'texlive/texlive:latest'
        # To make it fast, let's use a very popular lightweight one: 'ghcr.io/xu-cheng/texlive-full' or 'texlive/texlive' or 'paperist/alpine-texlive-ja'
        image = "paperist/alpine-texlive-ja"
        
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{temp_dir}:/workdir",
            "-w", "/workdir",
            image,
            "pdflatex", "resume.tex"
        ]
        
        try:
            print(f"Command: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            print("Exit code:", result.returncode)
            
            pdf_path = os.path.join(temp_dir, "resume.pdf")
            if os.path.exists(pdf_path):
                print("PDF successfully created!")
                return True
            else:
                print("PDF not found. Stderr:")
                print(result.stderr)
                print("Stdout:")
                print(result.stdout)
                return False
        except Exception as e:
            print("Failed to run docker compile:", e)
            return False

if __name__ == "__main__":
    test_docker_compile()
