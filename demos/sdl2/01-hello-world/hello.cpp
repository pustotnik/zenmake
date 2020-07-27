
#include <iostream>
#include <SDL.h>

const int WINDOW_WIDTH = 800;
const int WINDOW_HEIGHT = 600;

void loopEvents()
{
    SDL_Event event;
    while (true)
    {
        SDL_WaitEvent(&event);
        if (event.type == SDL_QUIT)
            break;
    }
}

int main()
{
    // check defines provided by ZenMake
    #if !defined(HAVE_SDL2) && !defined(SDL2)
        err err err // compiler error
    #endif

    #if !defined(SDL2_VERSION)
        err err err // compiler error
    #endif

    std::cout << "Running with SDL version: " << SDL2_VERSION << std::endl;

    if (SDL_Init(SDL_INIT_VIDEO) != 0)
    {
        std::cout << "SDL_Init Error: " << SDL_GetError() << std::endl;
        return 1;
    }

    int flags = 0;
    SDL_Window* window = SDL_CreateWindow(
        "Hello World!",
        SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
        WINDOW_WIDTH, WINDOW_HEIGHT,
        flags);

    if (!window)
    {
        std::cout << "SDL_CreateWindow Error: " << SDL_GetError() << std::endl;
        SDL_Quit();
        return 1;
    }

    SDL_Surface* surface = SDL_GetWindowSurface(window);

    //SDL_FillRect(surface, NULL, SDL_MapRGB(surface->format, 0xFF, 0xFF, 0xFF) );
    //SDL_FillRect(surface, NULL, SDL_MapRGB(surface->format, 0xFF, 0, 0) );
    SDL_FillRect(surface, NULL, SDL_MapRGB(surface->format, 60, 200, 200) );

    SDL_UpdateWindowSurface(window);

    loopEvents();

    SDL_DestroyWindow(window);

    SDL_Quit();

    std::cout << "Done." << std::endl;

    return 0;
}
