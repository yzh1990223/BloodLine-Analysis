import { FormEvent, useState } from "react";

interface SearchBarProps {
  defaultValue?: string;
  ariaLabel?: string;
  placeholder?: string;
  onSearch: (value: string) => void;
}

export function SearchBar({
  defaultValue = "",
  ariaLabel = "搜索数据表",
  placeholder = "搜索数据表",
  onSearch,
}: SearchBarProps) {
  // Keep local input state here so pages can stay focused on data fetching.
  const [value, setValue] = useState(defaultValue);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearch(value.trim());
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        aria-label={ariaLabel}
        placeholder={placeholder}
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
      <button type="submit">搜索</button>
    </form>
  );
}
