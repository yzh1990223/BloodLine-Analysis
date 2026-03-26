import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { TableSearchPage } from "../pages/TableSearchPage";

test("renders search input", () => {
  render(<TableSearchPage />);
  expect(screen.getByPlaceholderText("Search tables")).toBeTruthy();
});
