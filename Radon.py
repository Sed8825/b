import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import subprocess
import webbrowser
import os
import tempfile
import sys
import keyword
import google.generativeai as genai  # pip install google-generativeai

# Gemini API Setup
GENAI_API_KEY = ""  # Replace with your actual Gemini API key
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-pro")

class CodeEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Radon Code Editor")
        self.root.geometry("1200x700")

        self.filename = None
        self.language = tk.StringVar(value="Python")

        self.setup_ui()
        self.text_area.bind("<KeyRelease>", self.highlight_syntax)

    def setup_ui(self):
        sidebar = tk.Frame(self.root, height=30, bg="lightgray")
        sidebar.pack(side=tk.TOP, fill=tk.X)

        def create_tooltip(widget, text):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.withdraw()
            label = tk.Label(tooltip, text=text, background="white", relief='solid', borderwidth=1, font=("Arial", 10))
            label.pack()

            def enter(event):
                x = event.x_root + 10
                y = event.y_root + 10
                tooltip.wm_geometry(f"+{x}+{y}")
                tooltip.deiconify()

            def leave(event):
                tooltip.withdraw()

            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)

        buttons = [
            ("NF", "New File", self.new_file),
            ("NFo", "New Folder", self.new_folder),
            ("R", "Refresh", self.refresh),
            ("C", "Collapse All", self.collapse_all),
        ]
        for txt, tip, cmd in buttons:
            b = tk.Button(sidebar, text=txt, command=cmd, width=6)
            b.pack(side=tk.LEFT, padx=2, pady=2)
            create_tooltip(b, tip)

        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top_frame, text="Language:").pack(side=tk.LEFT, padx=5)
        lang_select = ttk.Combobox(top_frame, textvariable=self.language,
                                   values=["HTML", "CSS", "JavaScript", "Python", "C++"])
        lang_select.pack(side=tk.LEFT)
        lang_select.bind("<<ComboboxSelected>>", self.clear_output_on_lang_change)

        tk.Button(top_frame, text="Open", command=self.open_file).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Run", command=self.run_code).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Terminal", command=self.open_terminal).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Live Preview", command=self.preview_html).pack(side=tk.LEFT, padx=5)

        ai_button = tk.Button(top_frame, text="AI", command=self.open_ai_panel, bg="black", fg="white")
        ai_button.pack(side=tk.RIGHT, padx=5)
        create_tooltip(ai_button, "AI Help")

        main_area = tk.Frame(self.root)
        main_area.pack(fill=tk.BOTH, expand=1)

        self.text_area = tk.Text(main_area, wrap=tk.NONE, undo=True, font=("Consolas", 12))
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        # AI Panel with Entry Field at Bottom
        self.ai_container = tk.Frame(main_area, width=40, bg="#f5f5f5")
        self.ai_container.pack(side=tk.RIGHT, fill=tk.Y)
        self.ai_container.pack_forget()

        self.ai_panel = tk.Text(self.ai_container, height=25, bg="#f5f5f5", fg="black", wrap=tk.WORD)
        self.ai_panel.pack(fill=tk.BOTH, expand=True)
        self.ai_panel.insert(tk.END, "AI Help Output will appear here...\n")
        self.ai_panel.config(state=tk.DISABLED)

        self.ai_input = tk.Entry(self.ai_container)
        self.ai_input.pack(fill=tk.X)
        self.ai_input.bind("<Return>", self.ask_ai_help)

        self.text_area.tag_configure("keyword", foreground="blue")

        self.filepath_label = tk.Label(self.root, text="This file's src: None", anchor="w", bg="lightyellow")
        self.filepath_label.pack(fill=tk.X)

        output_label = tk.Label(self.root, text="Output:", bg="lightgray")
        output_label.pack(fill=tk.X)

        self.output = tk.Text(self.root, height=10, bg="black", fg="white")
        self.output.pack(fill=tk.X)
        self.output.insert(tk.END, "Output will appear here...\n")
        self.output.config(state=tk.DISABLED)

    def open_ai_panel(self):
        if self.ai_container.winfo_ismapped():
            self.ai_container.pack_forget()
        else:
            self.ai_container.pack(side=tk.RIGHT, fill=tk.Y)
            self.ai_panel.config(state=tk.NORMAL)
            self.ai_panel.delete("1.0", tk.END)
            self.ai_panel.insert(tk.END, "AI Help Output will appear here...\n")
            self.ai_panel.config(state=tk.DISABLED)
            self.ai_input.focus()

    def ask_ai_help(self, event=None):
        user_query = self.ai_input.get().strip()
        self.ai_input.delete(0, tk.END)
        if not user_query:
            return

        current_code = self.text_area.get("1.0", tk.END).strip()

        prompt = f"""
You are a coding assistant. The user is working in {self.language.get()}.
Here is the current code:

{current_code}

Now the user is asking:
"{user_query}"

Respond with only the modified or new code. Do not include markdown, ```python, ```html, or any triple backticks.
Just give clean code.
"""

        self.ai_panel.config(state=tk.NORMAL)
        self.ai_panel.insert(tk.END, "\nAsking AI for help...\n")
        self.ai_panel.config(state=tk.DISABLED)

        try:
            response = model.generate_content(prompt)
            new_code = response.text.strip()

            # Remove markdown formatting
            if new_code.startswith("```"):
                lines = new_code.splitlines()
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                new_code = "\n".join(lines)

            self.ai_panel.config(state=tk.NORMAL)
            self.ai_panel.insert(tk.END, "\n" + new_code + "\n")
            self.ai_panel.config(state=tk.DISABLED)

            apply = messagebox.askyesno("Insert AI Code", "Do you want to replace the editor code with the AI response?")
            if apply:
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert("1.0", new_code)
            else:
                self.text_area.insert(tk.END, "\n\n# AI Suggestion:\n" + new_code)

        except Exception as e:
            self.ai_panel.config(state=tk.NORMAL)
            self.ai_panel.insert(tk.END, f"\nError with Gemini API:\n{e}")
            self.ai_panel.config(state=tk.DISABLED)

    def clear_output_on_lang_change(self, event=None):
        self.output.config(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, f"Language changed to {self.language.get()}\n")
        self.output.config(state=tk.DISABLED)

    def new_file(self):
        self.text_area.delete("1.0", tk.END)
        self.filename = None
        self.filepath_label.config(text="This file's src: Unsaved File")

    def new_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            os.makedirs(os.path.join(folder, "NewFolder"), exist_ok=True)
            messagebox.showinfo("New Folder", "New folder created successfully.")

    def refresh(self):
        messagebox.showinfo("Refresh", "This would refresh the file explorer (to be implemented).")

    def collapse_all(self):
        messagebox.showinfo("Collapse", "This would collapse the folders (to be implemented).")

    def open_file(self):
        file = filedialog.askopenfilename(filetypes=[("All files", ".")])
        if file:
            self.filename = file
            with open(file, 'r') as f:
                content = f.read()
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert("1.0", content)
            self.filepath_label.config(text=f"This file's src: {file}")

    def save_file(self):
        file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("All files", ".")])
        if file:
            with open(file, 'w') as f:
                f.write(self.text_area.get("1.0", tk.END))
            self.filename = file
            self.filepath_label.config(text=f"This file's src: {file}")

    def run_code(self):
        lang = self.language.get()
        code = self.text_area.get("1.0", tk.END)
        self.output.config(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)

        try:
            if lang == "Python":
                with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode='w') as tf:
                    tf.write(code)
                    tf.close()
                    result = subprocess.run([sys.executable, tf.name], capture_output=True, text=True)
                    self.output.insert(tk.END, result.stdout + result.stderr)
            elif lang == "C++":
                with tempfile.NamedTemporaryFile(delete=False, suffix=".cpp", mode='w') as tf:
                    tf.write(code)
                    tf.close()
                    executable = tf.name + ".out"
                    compile_result = subprocess.run(["g++", tf.name, "-o", executable], capture_output=True, text=True)
                    if compile_result.returncode == 0:
                        run_result = subprocess.run([executable], capture_output=True, text=True)
                        self.output.insert(tk.END, run_result.stdout + run_result.stderr)
                    else:
                        self.output.insert(tk.END, compile_result.stderr)
            else:
                self.output.insert(tk.END, f"Run not supported for {lang}. Use 'Live Preview'.\n")

        except Exception as e:
            self.output.insert(tk.END, "Error occurred:\n" + str(e))

        self.output.config(state=tk.DISABLED)

    def open_terminal(self):
        try:
            if os.name == 'nt':
                subprocess.Popen("start cmd", shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Terminal"])
            elif os.name == 'posix':
                for term in ["gnome-terminal", "x-terminal-emulator", "konsole", "xfce4-terminal", "lxterminal", "xterm"]:
                    if subprocess.run(["which", term], capture_output=True).returncode == 0:
                        subprocess.Popen([term])
                        return
                messagebox.showerror("Terminal", "No terminal emulator found.")
            else:
                messagebox.showerror("OS Error", "Unsupported OS for launching terminal.")
        except Exception as e:
            messagebox.showerror("Terminal Error", str(e))

    def preview_html(self):
        lang = self.language.get()
        if lang not in ["HTML", "CSS", "JavaScript"]:
            messagebox.showinfo("Live Preview", "Live preview works only with HTML/CSS/JS.")
            return

        code = self.text_area.get("1.0", tk.END)

        if lang == "CSS":
            code = f"<style>\n{code}\n</style>"
        elif lang == "JavaScript":
            code = f"<script>\n{code}\n</script>"

        if "<html" not in code.lower():
            code = f"""<!DOCTYPE html>
<html>
<head>
<title>Live Preview</title>
</head>
<body>
{code}
</body>
</html>"""

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as tf:
            tf.write(code)
            tf.close()
            webbrowser.open(f"file://{tf.name}")

    def highlight_syntax(self, event=None):
        lang = self.language.get()
        self.text_area.tag_remove("keyword", "1.0", tk.END)

        if lang == "Python":
            keywords = keyword.kwlist
            content = self.text_area.get("1.0", tk.END)
            for word in keywords:
                start = "1.0"
                while True:
                    start = self.text_area.search(r'\b' + word + r'\b', start, stopindex=tk.END, regexp=True)
                    if not start:
                        break
                    end = f"{start}+{len(word)}c"
                    self.text_area.tag_add("keyword", start, end)
                    start = end

# ✅ Correct Bootstrapping
if __name__ == "__main__":
    root = tk.Tk()
    app = CodeEditorApp(root)
    root.mainloop()


