// Temporary AI Elements fallback components
import React from 'react'
import { cn } from '@/lib/utils'

export const Conversation = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-4", className)}
    {...props}
  />
))
Conversation.displayName = "Conversation"

export const ConversationContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex-1 overflow-y-auto", className)}
    {...props}
  />
))
ConversationContent.displayName = "ConversationContent"

export const ConversationScrollToBottom = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("", className)}
    {...props}
  />
))
ConversationScrollToBottom.displayName = "ConversationScrollToBottom"

export const Message = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { from?: string }
>(({ className, from, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex gap-3 p-4",
      from === "user" ? "justify-end" : "justify-start",
      className
    )}
    {...props}
  />
))
Message.displayName = "Message"

export const MessageContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex-1 space-y-2", className)}
    {...props}
  />
))
MessageContent.displayName = "MessageContent"

export const MessageAvatar = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { src?: string; name?: string }
>(({ className, src, name, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium", className)}
    {...props}
  >
    {name?.[0] || "A"}
  </div>
))
MessageAvatar.displayName = "MessageAvatar"

export const PromptInput = React.forwardRef<
  HTMLFormElement,
  React.FormHTMLAttributes<HTMLFormElement>
>(({ className, ...props }, ref) => (
  <form
    ref={ref}
    className={cn("space-y-2", className)}
    {...props}
  />
))
PromptInput.displayName = "PromptInput"

export const PromptInputTextarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    {...props}
  />
))
PromptInputTextarea.displayName = "PromptInputTextarea"

export const PromptInputActions = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex gap-2 justify-end", className)}
    {...props}
  />
))
PromptInputActions.displayName = "PromptInputActions"