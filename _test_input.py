import tkinter as tk
import sys
sys.path.insert(0, r"C:\Users\Administrator\TuringClaw")
sys.path.insert(0, r"C:\Users\Administrator")

import gui.chat as chat

original_init = chat.App.__init__
def patched_init(self, root):
    original_init(self, root)
    root.update_idletasks()
    root.update()
    
    print(f"Input exists: {hasattr(self, 'inp')}")
    print(f"Input winfo_exists: {self.inp.winfo_exists()}")
    print(f"Input size: {self.inp.winfo_width()} x {self.inp.winfo_height()}")
    print(f"Input pos: x={self.inp.winfo_x()}, y={self.inp.winfo_y()}")
    print(f"Input bg: {self.inp.cget('bg')}")
    print(f"Input fg: {self.inp.cget('fg')}")
    print(f"Input text: {self.inp.get()}")
    
    parent = self.inp.master
    print(f"Parent size: {parent.winfo_width()} x {parent.winfo_height()}")
    print(f"Parent pos: x={parent.winfo_x()}, y={parent.winfo_y()}")
    print(f"Root size: {root.winfo_width()} x {root.winfo_height()}")
    
    # Test typing programmatically
    self.inp.delete(0, tk.END)
    self.inp.insert(0, "test input works")
    result = self.inp.get()
    print(f"After insert: {result}")
    print(f"INPUT_TEST_OK" if result == "test input works" else "INPUT_TEST_FAIL")
    
    root.after(2000, root.destroy)

chat.App.__init__ = patched_init

root = tk.Tk()
app = chat.App(root)
root.mainloop()
