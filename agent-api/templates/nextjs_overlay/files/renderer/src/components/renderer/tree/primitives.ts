import type { ComponentType } from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type TPrimitive = ComponentType<Record<string, unknown>>;

/** The shadcn primitives a tree may name (`frontend_spec/trees.py` PRIMITIVES keeps the same list). */
export const PRIMITIVES: Record<string, TPrimitive> = {
  Tabs: Tabs as unknown as TPrimitive,
  TabsList: TabsList as unknown as TPrimitive,
  TabsTrigger: TabsTrigger as unknown as TPrimitive,
  TabsContent: TabsContent as unknown as TPrimitive,
  Sheet: Sheet as unknown as TPrimitive,
  SheetTrigger: SheetTrigger as unknown as TPrimitive,
  SheetContent: SheetContent as unknown as TPrimitive,
  SheetHeader: SheetHeader as unknown as TPrimitive,
  SheetTitle: SheetTitle as unknown as TPrimitive,
  SheetDescription: SheetDescription as unknown as TPrimitive,
  SheetFooter: SheetFooter as unknown as TPrimitive,
  Badge: Badge as unknown as TPrimitive,
  Button: Button as unknown as TPrimitive,
  Card: Card as unknown as TPrimitive,
  CardHeader: CardHeader as unknown as TPrimitive,
  CardTitle: CardTitle as unknown as TPrimitive,
  CardDescription: CardDescription as unknown as TPrimitive,
  CardContent: CardContent as unknown as TPrimitive,
  CardFooter: CardFooter as unknown as TPrimitive,
  Separator: Separator as unknown as TPrimitive,
  Accordion: Accordion as unknown as TPrimitive,
  AccordionItem: AccordionItem as unknown as TPrimitive,
  AccordionTrigger: AccordionTrigger as unknown as TPrimitive,
  AccordionContent: AccordionContent as unknown as TPrimitive,
  Table: Table as unknown as TPrimitive,
  TableHeader: TableHeader as unknown as TPrimitive,
  TableBody: TableBody as unknown as TPrimitive,
  TableRow: TableRow as unknown as TPrimitive,
  TableHead: TableHead as unknown as TPrimitive,
  TableCell: TableCell as unknown as TPrimitive,
  Avatar: Avatar as unknown as TPrimitive,
  AvatarImage: AvatarImage as unknown as TPrimitive,
  AvatarFallback: AvatarFallback as unknown as TPrimitive,
};
