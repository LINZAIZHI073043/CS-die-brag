# -*- coding: utf-8 -*-
"""
借口编辑器（图形界面）
可视化地增 / 删 / 改 CS2 死后狡辩的借口，改动自动保存到 excuses.txt。
主程序会实时读取该文件，所以改完立即生效，无需重启主程序。
"""

import os
import tkinter as tk
from tkinter import font, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXCUSES_FILE = os.path.join(SCRIPT_DIR, "excuses.txt")

HEADER = (
    "# CS2 死后狡辩 - 借口库\n"
    "# 一行一句。以 # 开头的行会被忽略（注释），空行也会忽略。\n"
    "# 想增删：直接用记事本改这个文件，或双击\"编辑借口.bat\"用图形界面改。\n"
    "# 改完立即生效，不用重启主程序。\n\n"
)


def load_items():
    if not os.path.exists(EXCUSES_FILE):
        return []
    with open(EXCUSES_FILE, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def save_items(items):
    with open(EXCUSES_FILE, "w", encoding="utf-8") as f:
        f.write(HEADER)
        for it in items:
            f.write(it + "\n")


class EditorApp:
    def __init__(self, root):
        self.root = root
        root.title("CS2 狡辩借口编辑器")
        root.geometry("480x560")
        self.items = load_items()

        big = font.Font(size=11)

        tk.Label(
            root,
            text="双击某一条可修改；下方输入新句子后点“添加”",
            fg="#555",
        ).pack(pady=(12, 6))

        # 列表 + 滚动条
        frame = tk.Frame(root)
        frame.pack(fill="both", expand=True, padx=12)
        self.listbox = tk.Listbox(
            frame, font=big, activestyle="none", selectmode="extended"
        )
        sb = tk.Scrollbar(frame, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", self.edit_selected)

        self.count_label = tk.Label(root, text="", fg="#777")
        self.count_label.pack(pady=(6, 0))

        # 输入 + 添加
        entry_frame = tk.Frame(root)
        entry_frame.pack(fill="x", padx=12, pady=8)
        self.entry = tk.Entry(entry_frame, font=big)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.add_item())
        tk.Button(entry_frame, text="添加", width=8, command=self.add_item).pack(
            side="left", padx=(8, 0)
        )

        # 删除 / 重载
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(
            btn_frame, text="删除选中", width=14, command=self.delete_selected
        ).pack(side="left")
        tk.Button(
            btn_frame, text="从文件重新载入", width=16, command=self.reload
        ).pack(side="left", padx=8)

        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for it in self.items:
            self.listbox.insert(tk.END, it)
        self.count_label.config(text=f"共 {len(self.items)} 条")

    def add_item(self):
        text = self.entry.get().strip()
        if not text:
            return
        if text in self.items:
            messagebox.showinfo("提示", "这条已经有了")
            return
        self.items.append(text)
        save_items(self.items)
        self.entry.delete(0, tk.END)
        self.refresh()
        self.listbox.see(tk.END)

    def delete_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            messagebox.showinfo("提示", "先在上面点选要删除的句子")
            return
        for i in reversed(sel):
            del self.items[i]
        save_items(self.items)
        self.refresh()

    def edit_selected(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        old = self.items[idx]

        top = tk.Toplevel(self.root)
        top.title("修改这一条")
        top.geometry("420x140")
        top.transient(self.root)
        top.grab_set()
        tk.Label(top, text="修改内容：").pack(pady=(14, 6))
        e = tk.Entry(top, width=42, font=font.Font(size=11))
        e.insert(0, old)
        e.pack(padx=14)
        e.focus_set()
        e.icursor(tk.END)

        def confirm():
            new = e.get().strip()
            if new:
                self.items[idx] = new
                save_items(self.items)
                self.refresh()
            top.destroy()

        tk.Button(top, text="保存", width=10, command=confirm).pack(pady=12)
        e.bind("<Return>", lambda ev: confirm())

    def reload(self):
        self.items = load_items()
        self.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    EditorApp(root)
    root.mainloop()
