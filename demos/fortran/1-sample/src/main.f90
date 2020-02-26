program main
    use calculator, only: add
    integer:: result
    call add (2,2,result)
    
    call printHelloWorld()
    
    include 'main_inc.f90'
    
    call printStatic()
    
end program main
