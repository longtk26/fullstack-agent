"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { siteConfig } from "@/config/site";

/** The navigation in a sheet on small screens. */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger render={<Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu" />}>
        <Menu />
      </SheetTrigger>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>{siteConfig.name}</SheetTitle>
        </SheetHeader>
        <nav aria-label="Mobile" className="flex flex-col gap-1 px-4">
          {siteConfig.navigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className="rounded-md px-3 py-2 text-foreground hover:bg-muted"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
