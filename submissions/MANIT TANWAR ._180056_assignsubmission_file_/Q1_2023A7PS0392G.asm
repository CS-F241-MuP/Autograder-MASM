.model small
.stack 100h
.data
    newline db 0dh, 0ah, '$'  ; newline characters
    num db ?
.code
main proc
    mov ax, @data
    mov ds, ax
    
    ; input single digit
    mov ah, 01h
    int 21h
    sub al, 30h        ; convert ascii to number
    mov num, al
    
    ; print newline
    ;lea dx, newline
    ;mov ah, 09h
    ;int 21h
    
    ; print 1 as first factor
    mov dl, '1'
    mov ah, 02h
    int 21h
    
    ; print space
    mov dl, ' '
    mov ah, 02h
    int 21h
    
    ; initialize counter
    mov cl, 1          ; start from 1
    
find_factors:
    inc cl
    mov al, num
    mov ah, 0
    div cl              ; divide num by current number
    
    cmp ah, 0          ; check remainder
    jne check_next     ; if not factor, check next number
    
    ; if factor found, print it
    mov dl, cl
    add dl, 30h        ; convert to ascii
    mov ah, 02h
    int 21h
    
    ; print space
    mov dl, ' '
    mov ah, 02h
    int 21h
    
check_next:
    cmp cl, num        ; check if we've reached the input number
    jb find_factors    ; if not, continue checking
    
    ; exit program
    mov ah, 4ch
    int 21h
main endp
end main
