// SPDX-License-Identifier: GPL-2.0-or-later
// Model-Author: Codex
// Scoped classic-console density. No registry or terminal-profile settings are written.
using System;
using System.Runtime.InteropServices;

public static class LiteConsoleDensity
{
    [StructLayout(LayoutKind.Sequential)]
    public struct Coord { public short X, Y; }
    [StructLayout(LayoutKind.Sequential)]
    public struct Rect { public short Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    public struct PixelRect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    public struct BufferInfo
    {
        public Coord Size, Cursor;
        public ushort Attributes;
        public Rect Window;
        public Coord Maximum;
    }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct FontInfo
    {
        public uint Size, Index;
        public Coord Cell;
        public uint Family, Weight;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
        public string Face;
    }
    public sealed class Session
    {
        public bool Applied, Changed;
        public int BeforeColumns, BeforeRows, AfterColumns, AfterRows;
        public string Message;
        public IntPtr Handle;
        public FontInfo Font;
        public BufferInfo Buffer;
    }

    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int id);
    [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr window, out PixelRect rect);
    [DllImport("kernel32.dll")] static extern bool GetConsoleScreenBufferInfo(IntPtr h, out BufferInfo b);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern bool GetCurrentConsoleFontEx(IntPtr h, bool maximum, ref FontInfo font);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern bool SetCurrentConsoleFontEx(IntPtr h, bool maximum, ref FontInfo font);
    [DllImport("kernel32.dll")] static extern bool SetConsoleScreenBufferSize(IntPtr h, Coord size);
    [DllImport("kernel32.dll")] static extern bool SetConsoleWindowInfo(IntPtr h, bool absolute, ref Rect r);
    [DllImport("kernel32.dll")] static extern bool SetConsoleCursorPosition(IntPtr h, Coord p);
    [DllImport("kernel32.dll")] static extern Coord GetLargestConsoleWindowSize(IntPtr h);

    public static Session Apply(int factor)
    {
        var state = new Session { Message = "HD: standardowa gestosc terminala." };
        if (factor <= 1 || Console.IsOutputRedirected) return state;
        PixelRect pixels;
        IntPtr window = GetConsoleWindow();
        // A pseudoconsole has no drawable host window. The host owns its font.
        if (window == IntPtr.Zero || !GetWindowRect(window, out pixels) ||
            pixels.Right - pixels.Left < 100 || pixels.Bottom - pixels.Top < 100 ||
            !String.IsNullOrEmpty(Environment.GetEnvironmentVariable("WT_SESSION")))
        {
            state.Message = "HD: host terminala ustawia czcionke. Zmniejsz ja Ctrl+- do 2x wiekszej siatki.";
            return state;
        }
        state.Handle = GetStdHandle(-11);
        state.Font = new FontInfo { Size = (uint)Marshal.SizeOf(typeof(FontInfo)) };
        if (!GetConsoleScreenBufferInfo(state.Handle, out state.Buffer) ||
            !GetCurrentConsoleFontEx(state.Handle, false, ref state.Font))
        {
            state.Message = "HD: ten terminal nie udostepnia zmiany czcionki; uzyj jego zoomu tekstu.";
            return state;
        }
        state.BeforeColumns = state.Buffer.Window.Right - state.Buffer.Window.Left + 1;
        state.BeforeRows = state.Buffer.Window.Bottom - state.Buffer.Window.Top + 1;
        FontInfo dense = state.Font;
        dense.Cell.X = (short)Math.Max(1, state.Font.Cell.X / factor);
        dense.Cell.Y = (short)Math.Max(2, state.Font.Cell.Y / factor);
        if (!SetCurrentConsoleFontEx(state.Handle, false, ref dense))
        {
            state.Message = "HD: czcionka nie pozwala na taka gestosc. Zmniejsz tekst recznie.";
            return state;
        }
        state.Changed = true;
        int columns = Math.Min(32000, state.BeforeColumns * factor);
        int rows = Math.Min(32000, state.BeforeRows * factor);
        Coord largest = GetLargestConsoleWindowSize(state.Handle);
        if (columns > largest.X || rows > largest.Y)
        {
            Restore(state);
            state.Message = "HD: wybrana czcionka/ekran nie miesci siatki 2x. Zwieksz okno lub zmniejsz tekst.";
            return state;
        }
        Coord buffer = new Coord {
            X = (short)Math.Max(state.Buffer.Size.X, columns),
            Y = (short)Math.Max(state.Buffer.Size.Y, rows) };
        Rect viewport = new Rect { Right = (short)(columns - 1), Bottom = (short)(rows - 1) };
        BufferInfo after;
        if (!SetConsoleScreenBufferSize(state.Handle, buffer) ||
            !SetConsoleWindowInfo(state.Handle, true, ref viewport) ||
            !GetConsoleScreenBufferInfo(state.Handle, out after))
        {
            Restore(state);
            state.Message = "HD: nie udalo sie powiekszyc siatki. Przywrocono ustawienia konsoli.";
            return state;
        }
        state.AfterColumns = after.Window.Right - after.Window.Left + 1;
        state.AfterRows = after.Window.Bottom - after.Window.Top + 1;
        state.Applied = state.AfterColumns >= columns && state.AfterRows >= rows;
        if (!state.Applied) Restore(state);
        state.Message = state.Applied ? String.Format("HD {0}x: {1}x{2} -> {3}x{4} komorek.",
            factor, state.BeforeColumns, state.BeforeRows, state.AfterColumns, state.AfterRows) :
            "HD: host nie potwierdzil wiekszej siatki; przywrocono ustawienia.";
        return state;
    }

    public static void Restore(Session state)
    {
        if (state == null || !state.Changed) return;
        Rect viewport = state.Buffer.Window;
        SetConsoleWindowInfo(state.Handle, true, ref viewport);
        BufferInfo current;
        if (GetConsoleScreenBufferInfo(state.Handle, out current))
        {
            Coord cursor = new Coord {
                X = (short)Math.Min(current.Cursor.X, state.Buffer.Size.X - 1),
                Y = (short)Math.Min(current.Cursor.Y, state.Buffer.Size.Y - 1) };
            SetConsoleCursorPosition(state.Handle, cursor);
        }
        SetConsoleScreenBufferSize(state.Handle, state.Buffer.Size);
        FontInfo font = state.Font;
        SetCurrentConsoleFontEx(state.Handle, false, ref font);
        SetConsoleWindowInfo(state.Handle, true, ref viewport);
        state.Changed = false;
    }
}
