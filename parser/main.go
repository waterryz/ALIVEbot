package main

import (
	"context"
	"encoding/base64"
	"net/http"
	"os"
	"time"

	"github.com/chromedp/chromedp"
	"github.com/gin-gonic/gin"
)

type Credentials struct {
	Login    string `json:"login"`
	Password string `json:"password"`
}

func parseSmartNation(login, pass string) (string, error) {
	ctx, cancel := chromedp.NewContext(context.Background())
	defer cancel()

	ctx, cancel = context.WithTimeout(ctx, 45*time.Second)
	defer cancel()

	loginURL := "https://college.snation.kz/kz/tko/login"
	journalURL := "https://college.snation.kz/kz/tko/control/journals/873776"

	var screenshot []byte
	err := chromedp.Run(ctx,
		chromedp.Navigate(loginURL),
		chromedp.Sleep(2*time.Second),
		chromedp.SendKeys(`input[name="username"]`, login),
		chromedp.SendKeys(`input[name="password"]`, pass),
		chromedp.Click(`button[type="submit"]`),
		chromedp.Sleep(3*time.Second),
		chromedp.Navigate(journalURL),
		chromedp.Sleep(3*time.Second),
		chromedp.FullScreenshot(&screenshot, 90),
	)
	if err != nil {
		return "", err
	}

	return base64.StdEncoding.EncodeToString(screenshot), nil
}

func main() {
	r := gin.Default()

	r.POST("/parse", func(c *gin.Context) {
		var creds Credentials
		if err := c.ShouldBindJSON(&creds); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
			return
		}

		img, err := parseSmartNation(creds.Login, creds.Password)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"image": img})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	r.Run("0.0.0.0:" + port)
}
