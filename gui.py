import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from woo_csv_fix import run_woocsvfix


def run_job(src, outdir):
    s = run_woocsvfix(src, outdir)
    return [f"Product rows (all preserved): {s['rows']}",
            f"Automatic fixes applied: {len(s['fixes'])}",
            f"Blocking issues to decide: {len(s['blocking'])}",
            f"Re-check: {'PASS' if s['recheck_ok'] else 'FAIL'}",
            f"Fixed CSV: {s['fixed_path']}",
            f"Report: {s['report_path']}"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WooCsvFix")
        self.geometry("640x520")
        self.resizable(False, False)
        self.file = tk.StringVar()
        row = tk.Frame(self); row.pack(fill="x", padx=12, pady=(12, 2))
        tk.Label(row, text="Product CSV file:", width=34, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.file, width=38).pack(side="left")
        tk.Button(row, text="Browse", command=lambda: self.pick(self.file,
                  [("CSV files", "*.csv"), ("All files", "*.*")])).pack(side="left", padx=4)
        tk.Button(self, text="Check, fix && re-check", font=("Segoe UI", 11, "bold"),
                  command=self.start).pack(pady=10)
        self.log = scrolledtext.ScrolledText(self, width=76, height=16,
                                             font=("Consolas", 9))
        self.log.pack(padx=12, pady=4)
        self.write("Pick the product CSV you are about to import into WooCommerce. The original file is never modified.")

    def write(self, msg):
        self.log.insert(tk.END, str(msg) + "\n")
        self.log.see(tk.END)
        self.update_idletasks()

    def pick(self, var, types):
        p = filedialog.askopenfilename(filetypes=types)
        if p:
            var.set(p)
    def collect(self):
        src = self.file.get().strip()
        if not src or not os.path.isfile(src):
            raise ValueError("Choose a product CSV file first.")
        return (src, os.path.join(os.path.dirname(src), "woocsvfix_out"))

    def start(self):
        try:
            args = self.collect()
        except Exception as e:
            messagebox.showerror("WooCsvFix", str(e))
            return
        self.write("Working... (the window stays responsive)")
        threading.Thread(target=self._run, args=args, daemon=True).start()

    def _run(self, *args):
        try:
            lines = run_job(*args)
            for line in lines:
                self.after(0, self.write, line)
        except Exception as e:
            self.after(0, self.write, f"ERROR: {e}")


if __name__ == "__main__":
    App().mainloop()
