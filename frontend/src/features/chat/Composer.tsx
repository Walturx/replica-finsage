import { ArrowUp, Square } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent } from "react";

interface Props {
  busy: boolean;
  disabled?: boolean;
  placeholder?: string;
  onSend: (text: string) => void;
  onStop: () => void;
}

export function Composer({ busy, disabled, placeholder = "Ask about a 10-K, 10-Q or earnings report", onSend, onStop }: Props) {
  const [value, setValue] = useState("");
  const canSend = value.trim().length > 0 && !busy && !disabled;

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    if (!canSend) return;
    onSend(value.trim());
    setValue("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form
      onSubmit={submit}
      className="flex items-end gap-2 rounded-[28px] border border-transparent bg-muted py-2 pl-5 pr-2 transition-colors focus-within:border-border-strong"
    >
      <label htmlFor="composer" className="sr-only">
        Message
      </label>
      <textarea
        id="composer"
        rows={1}
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        className="max-h-48 min-h-[28px] flex-1 resize-none bg-transparent py-1.5 text-[15px] leading-relaxed outline-none [field-sizing:content] placeholder:text-muted-foreground disabled:opacity-50"
      />
      {busy ? (
        <button
          type="button"
          onClick={onStop}
          aria-label="Stop"
          className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-foreground text-background"
        >
          <Square className="h-3.5 w-3.5 fill-current" />
        </button>
      ) : (
        <button
          type="submit"
          disabled={!canSend}
          aria-label="Send"
          className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-foreground text-background transition-opacity disabled:cursor-default disabled:opacity-25"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      )}
    </form>
  );
}
